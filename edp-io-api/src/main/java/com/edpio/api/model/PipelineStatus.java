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
@Schema(description = "Pipeline status information")
public class PipelineStatus {
    
    @Schema(example = "oracle_customers")
    private String pipelineName;
    
    @Schema(example = "HEALTHY", allowableValues = {"HEALTHY", "WARNING", "ERROR"})
    private String status;
    
    @Schema(example = "15 min ago")
    private String lastRun;
    
    @Schema(example = "1247")
    private Long recordsProcessed;
    
    @Schema(example = "0")
    private Integer errorCount;
    
    @Schema(example = "42.5")
    private Double durationSeconds;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Pipeline status response")
class PipelineStatusResponse {
    private List<PipelineStatus> pipelines;
    private Integer totalCount;
    private Integer healthyCount;
}
