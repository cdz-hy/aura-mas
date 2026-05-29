package com.learning.typehandler;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class JsonStringTypeHandlerTest {

    @Test
    void serializesBareStringAsJsonString() throws Exception {
        assertEquals("\"text\"", JsonStringTypeHandler.toDatabaseJson("text"));
        assertEquals("\"summary\"", JsonStringTypeHandler.toDatabaseJson("summary"));
    }

    @Test
    void leavesExistingJsonValuesUntouched() throws Exception {
        assertEquals("{\"chain\":[\"rag\",\"orchestrator\"]}",
                JsonStringTypeHandler.toDatabaseJson("{\"chain\":[\"rag\",\"orchestrator\"]}"));
        assertEquals("[\"rag\",\"orchestrator\"]",
                JsonStringTypeHandler.toDatabaseJson("[\"rag\",\"orchestrator\"]"));
    }

    @Test
    void deserializesJsonStringBackToPlainString() throws Exception {
        assertEquals("text", JsonStringTypeHandler.fromDatabaseJson("\"text\""));
        assertEquals("summary", JsonStringTypeHandler.fromDatabaseJson("\"summary\""));
    }

    @Test
    void returnsStructuredJsonAsCompactJsonText() throws Exception {
        assertEquals("{\"chain\":[\"rag\",\"orchestrator\"]}",
                JsonStringTypeHandler.fromDatabaseJson("{\"chain\":[\"rag\",\"orchestrator\"]}"));
    }

    @Test
    void mapsBlankInputToNullForOptionalColumn() throws Exception {
        assertNull(JsonStringTypeHandler.toDatabaseJson(""));
        assertNull(JsonStringTypeHandler.toDatabaseJson("   "));
    }
}
