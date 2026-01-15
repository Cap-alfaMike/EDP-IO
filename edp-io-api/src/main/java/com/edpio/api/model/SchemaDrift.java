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
@Schema(description = "Schema column definition")
public class SchemaColumn {
    
    @Schema(example = "customer_id")
    private String name;
    
    @Schema(example = "STRING")
    private String dataType;
    
    @Schema(example = "false")
    private Boolean nullable;
    
    @Schema(example = "Unique customer identifier")
    private String description;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Schema drift detection result")
class SchemaDriftResult {
    
    @Schema(example = "COLUMN_ADDED")
    private String changeType;
    
    @Schema(example = "loyalty_points")
    private String columnName;
    
    @Schema(example = "WARNING")
    private String severity;
    
    @Schema(example = "New column added to source system")
    private String description;
    
    @Schema(example = "Update data contract and reload data")
    private String recommendedAction;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Lineage node")
class LineageNode {
    
    @Schema(example = "bronze.customers")
    private String id;
    
    @Schema(example = "customers")
    private String label;
    
    @Schema(example = "bronze")
    private String layer;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Lineage edge/dependency")
class LineageEdge {
    
    @Schema(example = "oracle.customers")
    private String source;
    
    @Schema(example = "bronze.customers")
    private String target;
}
