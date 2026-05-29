package com.learning.typehandler;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedTypes;

import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * Stores a Java String in a MySQL JSON column while keeping the entity API as a plain String.
 */
@MappedTypes(String.class)
public class JsonStringTypeHandler extends BaseTypeHandler<String> {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, String parameter, JdbcType jdbcType)
            throws SQLException {
        ps.setString(i, toDatabaseJson(parameter));
    }

    @Override
    public String getNullableResult(ResultSet rs, String columnName) throws SQLException {
        return fromDatabaseJson(rs.getString(columnName));
    }

    @Override
    public String getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        return fromDatabaseJson(rs.getString(columnIndex));
    }

    @Override
    public String getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        return fromDatabaseJson(cs.getString(columnIndex));
    }

    public static String toDatabaseJson(String value) throws SQLException {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            return null;
        }
        if (isJson(trimmed)) {
            return trimmed;
        }
        try {
            return OBJECT_MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new SQLException("Failed to serialize string as JSON", e);
        }
    }

    public static String fromDatabaseJson(String json) throws SQLException {
        if (json == null) {
            return null;
        }
        String trimmed = json.trim();
        if (trimmed.isEmpty()) {
            return "";
        }
        try {
            JsonNode node = OBJECT_MAPPER.readTree(trimmed);
            return node.isTextual() ? node.asText() : node.toString();
        } catch (Exception e) {
            return json;
        }
    }

    private static boolean isJson(String value) {
        try {
            OBJECT_MAPPER.readTree(value);
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }
}
