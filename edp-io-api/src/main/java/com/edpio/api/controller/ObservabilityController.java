package com.edpio.api.controller;

import com.edpio.api.model.Alert;
import com.edpio.api.service.ObservabilityService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;

/**
 * REST Controller for observability, alerts, and incident intelligence.
 * Endpoints: GET /api/alerts, GET /api/schema-drift/{table}, GET /api/lineage/{table}
 */
@Slf4j
@RestController
@RequestMapping("/api")
@Tag(name = "Observability", description = "Alerts, schema drift detection, and lineage endpoints")
@RequiredArgsConstructor
public class ObservabilityController {
    
    private final ObservabilityService observabilityService;
    
    @Operation(summary = "Get active alerts", description = "Returns current alerts from monitoring system")
    @GetMapping("/alerts")
    public ResponseEntity<Map<String, Object>> getAlerts() {
        log.info("GET /api/alerts - Fetching active alerts");
        List<Alert> alerts = observabilityService.getAlerts();
        return ResponseEntity.ok(Map.of(
            "alerts", alerts,
            "critical_count", (int) alerts.stream().filter(a -> "ERROR".equals(a.getSeverity()) || "CRITICAL".equals(a.getSeverity())).count(),
            "warning_count", (int) alerts.stream().filter(a -> "WARNING".equals(a.getSeverity())).count()
        ));
    }
    
    @Operation(summary = "Detect schema drift", description = "Check for schema changes in a table and assess business impact")
    @GetMapping("/schema-drift/{table}")
    public ResponseEntity<Map<String, Object>> detectSchemaDrift(@PathVariable String table) {
        log.info("GET /api/schema-drift/{} - Detecting schema drift", table);
        Map<String, Object> result = observabilityService.detectSchemaDrift(table);
        return ResponseEntity.ok(result);
    }
    
    @Operation(summary = "Get data lineage", description = "Returns upstream and downstream dependencies for a table")
    @GetMapping("/lineage/{table}")
    public ResponseEntity<Map<String, Object>> getLineage(@PathVariable String table) {
        log.info("GET /api/lineage/{} - Fetching data lineage", table);
        Map<String, Object> lineage = observabilityService.getLineage(table);
        return ResponseEntity.ok(lineage);
    }
}
