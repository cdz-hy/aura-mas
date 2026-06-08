package com.learning.common;

import lombok.Getter;

@Getter
public enum ErrorCode {

    SUCCESS(200, "操作成功"),
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未登录或token已过期"),
    FORBIDDEN(403, "权限不足"),
    NOT_FOUND(404, "资源不存在"),
    INTERNAL_ERROR(500, "服务器内部错误"),

    USER_NOT_FOUND(1001, "用户不存在"),
    USER_ALREADY_EXISTS(1002, "用户已存在"),
    PASSWORD_ERROR(1003, "密码错误"),
    ACCOUNT_DISABLED(1004, "账户已被禁用"),

    PLAN_NOT_FOUND(2001, "学习计划不存在"),
    RESOURCE_NOT_FOUND(2002, "学习资源不存在"),
    TASK_NOT_FOUND(2003, "任务不存在"),
    NOTE_NOT_FOUND(2004, "笔记不存在"),
    FLASHCARD_NOT_FOUND(2005, "闪卡不存在"),

    FILE_UPLOAD_ERROR(3001, "文件上传失败"),
    FILE_NOT_FOUND(3002, "文件不存在"),

    MQ_SEND_ERROR(4001, "消息发送失败");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }
}
