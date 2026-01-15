package com.edpio.api.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Data quality metrics")
public class DataQualityMetrics {
    
    @Schema(example = "dim_customer")
    private String tableName;
    
    @Schema(example = "98.7")
    private Double qualityScore;
    
    @Schema(example = "45")
    private Integer rowCount;
    
    @Schema(example = "12")
    private Integer columnCount;
    
    @Schema(example = "0")
    private Integer nullViolations;
    
    @Schema(example = "2")
    private Integer uniqueViolations;
    
    @Schema(example = "0")
    private Integer typeViolations;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Data quality response")
class DataQualityResponse {
    private List<DataQualityMetrics> tables;
    private Double overallScore;
    private String lastValidated;
}
