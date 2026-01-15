package com.edpio.api.service;

import com.edpio.api.model.PipelineStatus;
import com.edpio.api.provider.DatabricksProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import java.util.*;

/**
 * Service for pipeline orchestration and status monitoring.
 * Tracks Airflow DAG execution and provides pipeline health metrics.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PipelineService {
    
    private final DatabricksProvider databricksProvider;
    
    /**
     * Get status of all data pipelines.
     * Mirrors Python render_pipeline_summary() function.
     */
    public List<PipelineStatus> getPipelineStatus() {
        List<PipelineStatus> pipelines = new ArrayList<>();
        
        // In production: Query Airflow metadata DB or observability tables
        // SELECT dag_id, state, end_date FROM airflow.dag_run WHERE is_active = true
        
        pipelines.add(PipelineStatus.builder()
                .pipelineName("oracle_customers")
                .status("HEALTHY")
                .lastRun("15 min ago")
                .recordsProcessed(1247L)
                .errorCount(0)
                .durationSeconds(42.5)
                .build());
        
        pipelines.add(PipelineStatus.builder()
                .pipelineName("oracle_products")
                .status("HEALTHY")
                .lastRun("22 min ago")
                .recordsProcessed(583L)
                .errorCount(0)
                .durationSeconds(38.2)
                .build());
        
        pipelines.add(PipelineStatus.builder()
                .pipelineName("sqlserver_orders")
                .status("WARNING")
                .lastRun("1h 30min ago")
                .recordsProcessed(5892L)
                .errorCount(1)
                .durationSeconds(95.7)
                .build());
        
        pipelines.add(PipelineStatus.builder()
                .pipelineName("sqlserver_order_items")
                .status("HEALTHY")
                .lastRun("1h 30min ago")
                .recordsProcessed(18234L)
                .errorCount(0)
                .durationSeconds(142.3)
                .build());
        
        pipelines.add(PipelineStatus.builder()
                .pipelineName("dbt_silver_layer")
                .status("HEALTHY")
                .lastRun("45 min ago")
                .recordsProcessed(0L)  // dbt doesn't count records
                .errorCount(0)
                .durationSeconds(180.5)
                .build());
        
        pipelines.add(PipelineStatus.builder()
                .pipelineName("dbt_gold_layer")
                .status("HEALTHY")
                .lastRun("45 min ago")
                .recordsProcessed(0L)
                .errorCount(0)
                .durationSeconds(225.8)
                .build());
        
        return pipelines;
    }
    
    /**
     * Get status of specific pipeline.
     */
    public PipelineStatus getPipelineStatus(String pipelineName) {
        return getPipelineStatus().stream()
                .filter(p -> p.getPipelineName().equalsIgnoreCase(pipelineName))
                .findFirst()
                .orElse(null);
    }
    
    /**
     * Trigger pipeline execution.
     * In production: Would call Airflow REST API.
     */
    public Map<String, Object> triggerPipeline(String pipelineName) {
        try {
            // In production: Call Airflow API
            // POST /api/v1/dags/{dag_id}/dagRuns
            
            return Map.of(
                "pipeline", pipelineName,
                "status", "TRIGGERED",
                "run_id", UUID.randomUUID().toString(),
                "timestamp", System.currentTimeMillis()
            );
        } catch (Exception e) {
            log.error("Failed to trigger pipeline {}", pipelineName, e);
            return Map.of("error", e.getMessage());
        }
    }
    
    /**
     * Get pipeline execution history.
     */
    public List<Map<String, Object>> getPipelineHistory(String pipelineName, int limit) {
        List<Map<String, Object>> history = new ArrayList<>();
        
        // In production: Query Airflow runs table
        for (int i = 0; i < Math.min(limit, 5); i++) {
            history.add(Map.of(
                "run_id", UUID.randomUUID().toString(),
                "status", i == 0 ? "RUNNING" : "SUCCESS",
                "start_time", System.currentTimeMillis() - (i * 3600000),
                "end_time", System.currentTimeMillis() - ((i - 1) * 3600000),
                "duration_seconds", 120.5 + i * 10
            ));
        }
        
        return history;
    }
}
