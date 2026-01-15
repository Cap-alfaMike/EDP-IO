package com.edpio.api.controller;

import com.edpio.api.model.DataQualityMetrics;
import com.edpio.api.service.DataQualityService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;

/**
 * REST Controller for data quality monitoring.
 * Endpoints: GET /api/data-quality, POST /api/data-quality/{table}/test
 */
@Slf4j
@RestController
@RequestMapping("/api/data-quality")
@Tag(name = "Data Quality", description = "Data quality metrics and testing endpoints")
@RequiredArgsConstructor
public class DataQualityController {
    
    private final DataQualityService dataQualityService;
    
    @Operation(summary = "Get quality metrics for all tables", description = "Returns null violations, unique violations, type violations, and overall quality score")
    @GetMapping
    public ResponseEntity<Map<String, Object>> getQualityMetrics() {
        log.info("GET /api/data-quality - Fetching quality metrics for all tables");
        List<DataQualityMetrics> metrics = dataQualityService.getQualityMetrics();
        
        double overallScore = metrics.stream()
                .mapToDouble(DataQualityMetrics::getQualityScore)
                .average()
                .orElse(0.0);
        
        return ResponseEntity.ok(Map.of(
            "tables", metrics,
            "overall_score", overallScore,
            "last_validated", System.currentTimeMillis()
        ));
    }
    
    @Operation(summary = "Get quality metrics for specific table", description = "Returns detailed quality metrics for a single table")
    @GetMapping("/{table}")
    public ResponseEntity<DataQualityMetrics> getTableQuality(@PathVariable String table) {
        log.info("GET /api/data-quality/{} - Fetching quality metrics", table);
        DataQualityMetrics metrics = dataQualityService.getTableQuality(table);
        if (metrics == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(metrics);
    }
    
    @Operation(summary = "Run quality tests", description = "Executes dbt tests for a specific table")
    @PostMapping("/{table}/test")
    public ResponseEntity<Map<String, Object>> runQualityTests(@PathVariable String table) {
        log.info("POST /api/data-quality/{}/test - Running quality tests", table);
        Map<String, Object> result = dataQualityService.runQualityTests(table);
        return ResponseEntity.ok(result);
    }
}
