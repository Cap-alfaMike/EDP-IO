package com.edpio.api.controller;

import com.edpio.api.model.PipelineStatus;
import com.edpio.api.service.PipelineService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;

/**
 * REST Controller for pipeline orchestration and monitoring.
 * Endpoints: GET /api/pipelines, POST /api/pipelines/{name}/trigger
 */
@Slf4j
@RestController
@RequestMapping("/api/pipelines")
@Tag(name = "Pipelines", description = "Pipeline status and orchestration endpoints")
@RequiredArgsConstructor
public class PipelineController {
    
    private final PipelineService pipelineService;
    
    @Operation(summary = "Get all pipeline statuses", description = "Returns status of all data pipelines (ingestion, dbt, observability)")
    @GetMapping
    public ResponseEntity<List<PipelineStatus>> getPipelines() {
        log.info("GET /api/pipelines - Fetching all pipeline statuses");
        List<PipelineStatus> pipelines = pipelineService.getPipelineStatus();
        return ResponseEntity.ok(pipelines);
    }
    
    @Operation(summary = "Get specific pipeline status", description = "Returns detailed status for a single pipeline")
    @GetMapping("/{name}")
    public ResponseEntity<PipelineStatus> getPipeline(@PathVariable String name) {
        log.info("GET /api/pipelines/{} - Fetching pipeline status", name);
        PipelineStatus pipeline = pipelineService.getPipelineStatus(name);
        if (pipeline == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(pipeline);
    }
    
    @Operation(summary = "Trigger pipeline execution", description = "Manually trigger a pipeline run (calls Airflow API)")
    @PostMapping("/{name}/trigger")
    public ResponseEntity<Map<String, Object>> triggerPipeline(@PathVariable String name) {
        log.info("POST /api/pipelines/{}/trigger - Triggering pipeline execution", name);
        Map<String, Object> result = pipelineService.triggerPipeline(name);
        return ResponseEntity.ok(result);
    }
    
    @Operation(summary = "Get pipeline execution history", description = "Returns recent runs of a pipeline")
    @GetMapping("/{name}/history")
    public ResponseEntity<List<Map<String, Object>>> getPipelineHistory(
            @PathVariable String name,
            @RequestParam(defaultValue = "10") int limit) {
        log.info("GET /api/pipelines/{}/history - Fetching pipeline history", name);
        List<Map<String, Object>> history = pipelineService.getPipelineHistory(name, limit);
        return ResponseEntity.ok(history);
    }
}
