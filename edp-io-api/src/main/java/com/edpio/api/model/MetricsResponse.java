package com.edpio.api.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import io.swagger.v3.oas.annotations.media.Schema;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Pipeline metrics and KPIs")
public class MetricsResponse {
    
    @Schema(example = "2847293")
    private Long totalRecords;
    
    @Schema(example = "12")
    private Integer tablesMonitored;
    
    @Schema(example = "11")
    private Integer pipelinesHealthy;
    
    @Schema(example = "12")
    private Integer pipelinesTotal;
    
    @Schema(example = "98.7")
    private Double qualityScore;
    
    @Schema(example = "1.5")
    private Double dataFreshnessHours;
    
    @Schema(example = "2")
    private Integer alertsOpen;
    
    @Schema(example = "2024-01-15T14:30:00Z")
    private String lastUpdated;
}
