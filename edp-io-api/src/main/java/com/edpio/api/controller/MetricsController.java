package com.edpio.api.controller;

import com.edpio.api.model.MetricsResponse;
import com.edpio.api.service.MetricsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * REST Controller for platform metrics and KPIs.
 * Endpoint: GET /api/metrics
 */
@Slf4j
@RestController
@RequestMapping("/api/metrics")
@Tag(name = "Metrics", description = "Platform metrics and KPI endpoints")
@RequiredArgsConstructor
public class MetricsController {
    
    private final MetricsService metricsService;
    
    @Operation(summary = "Get platform metrics", description = "Returns KPIs: total records, pipeline health, data quality score, freshness")
    @GetMapping
    public ResponseEntity<MetricsResponse> getMetrics() {
        log.info("GET /api/metrics - Fetching platform metrics");
        MetricsResponse metrics = metricsService.getMetrics();
        return ResponseEntity.ok(metrics);
    }
}
