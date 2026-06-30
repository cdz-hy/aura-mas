package com.learning.common;

public final class OperationType {

    private OperationType() {}

    // ==================== 认证模块 ====================
    public static final String LOGIN = "LOGIN";
    public static final String LOGIN_FAIL = "LOGIN_FAIL";
    public static final String REGISTER = "REGISTER";

    // ==================== 管理员-用户管理 ====================
    public static final String ADMIN_CREATE_USER = "ADMIN_CREATE_USER";
    public static final String ADMIN_UPDATE_USER = "ADMIN_UPDATE_USER";
    public static final String ADMIN_DELETE_USER = "ADMIN_DELETE_USER";
    public static final String ADMIN_TOGGLE_STATUS = "ADMIN_TOGGLE_STATUS";
    public static final String ADMIN_CHANGE_ROLE = "ADMIN_CHANGE_ROLE";
    public static final String ADMIN_BATCH_TOGGLE_STATUS = "ADMIN_BATCH_TOGGLE_STATUS";
    public static final String ADMIN_BATCH_DELETE_USER = "ADMIN_BATCH_DELETE_USER";

    // ==================== 管理员-知识库 ====================
    public static final String KB_CREATE = "KB_CREATE";
    public static final String KB_DELETE = "KB_DELETE";

    // ==================== 用户个人信息 ====================
    public static final String USER_UPDATE_INFO = "USER_UPDATE_INFO";
    public static final String USER_UPDATE_PROFILE = "USER_UPDATE_PROFILE";
    public static final String USER_UPDATE_BEHAVIOR = "USER_UPDATE_BEHAVIOR";
    public static final String USER_UPLOAD_AVATAR = "USER_UPLOAD_AVATAR";
    public static final String USER_CLEAR_AVATAR = "USER_CLEAR_AVATAR";
    public static final String USER_DELETE_ACCOUNT = "USER_DELETE_ACCOUNT";

    // ==================== 学习计划 ====================
    public static final String PLAN_CREATE = "PLAN_CREATE";
    public static final String PLAN_UPDATE = "PLAN_UPDATE";
    public static final String PLAN_DELETE = "PLAN_DELETE";
    public static final String PLAN_STATUS_CHANGE = "PLAN_STATUS_CHANGE";

    // ==================== 知识图谱 ====================
    public static final String KG_CREATE_DOMAIN = "KG_CREATE_DOMAIN";
    public static final String KG_UPDATE_DOMAIN = "KG_UPDATE_DOMAIN";
    public static final String KG_DELETE_DOMAIN = "KG_DELETE_DOMAIN";
    public static final String KG_PATCH_NODE = "KG_PATCH_NODE";
    public static final String KG_DELETE_NODE = "KG_DELETE_NODE";

    // ==================== 笔记 ====================
    public static final String NOTE_CREATE = "NOTE_CREATE";
    public static final String NOTE_UPDATE = "NOTE_UPDATE";
    public static final String NOTE_DELETE = "NOTE_DELETE";

    // ==================== 学习资源 ====================
    public static final String RESOURCE_CREATE = "RESOURCE_CREATE";
    public static final String RESOURCE_DELETE = "RESOURCE_DELETE";
    public static final String RESOURCE_UPDATE_CONTENT = "RESOURCE_UPDATE_CONTENT";
    public static final String RESOURCE_BULK_CREATE = "RESOURCE_BULK_CREATE";

    // ==================== 闪卡 ====================
    public static final String FLASHCARD_SAVE = "FLASHCARD_SAVE";
    public static final String FLASHCARD_REVIEW = "FLASHCARD_REVIEW";
    public static final String FLASHCARD_DELETE = "FLASHCARD_DELETE";

    // ==================== 文件 ====================
    public static final String FILE_UPLOAD = "FILE_UPLOAD";

    // ==================== 票据 ====================
    public static final String TICKET_ISSUE = "TICKET_ISSUE";

    // ==================== 对话 ====================
    public static final String DIALOGUE_DELETE_SESSION = "DIALOGUE_DELETE_SESSION";
    public static final String DIALOGUE_DELETE_MESSAGE = "DIALOGUE_DELETE_MESSAGE";
    public static final String DIALOGUE_BATCH_DELETE = "DIALOGUE_BATCH_DELETE";
}
