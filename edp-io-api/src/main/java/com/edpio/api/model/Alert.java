package com.edpio.api.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Alert notification")
public class Alert {
    
    @Schema(example = "WARNING", allowableValues = {"INFO", "WARNING", "ERROR", "CRITICAL"})
    private String severity;
    
    @Schema(example = "Schema Drift Detected")
    private String title;
    
    @Schema(example = "New column 'loyalty_points' in Oracle CRM customers table")
    private String description;
    
    @Schema(example = "2 hours ago")
    private String timestamp;
    
    @Schema(example = "Update data contract")
    private String recommendedAction;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Alerts response")
class AlertsResponse {
    private List<Alert> alerts;
    private Integer criticalCount;
    private Integer warningCount;
}
