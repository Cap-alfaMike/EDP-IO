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
@Schema(description = "Chat message for Ask the Architect")
public class ChatMessage {
    
    @Schema(example = "user", allowableValues = {"user", "assistant"})
    private String role;
    
    @Schema(example = "Why did the Oracle ingestion fail?")
    private String content;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Chat request")
class ChatRequest {
    private String message;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Chat response")
class ChatResponse {
    private String response;
    private String model;
    private Long inputTokens;
    private Long outputTokens;
}
