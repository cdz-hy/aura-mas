package com.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("resource_library")
public class ResourceLibrary {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 资源标题 */
    private String title;

    /** 内容类型: text / image / rich */
    private String contentType;

    /** 文本内容 (text 类型) */
    private String content;

    /** 图片 URL (image 类型) */
    private String imageUrl;

    /** 图片描述 (image 类型) */
    private String imageCaption;

    /** Qdrant 中的 doc_id，用于关联向量数据 */
    private Long qdrantDocId;

    /** 状态: 0=待审核, 1=已入库, 2=已拒绝 */
    private Integer status;

    /** 创建者用户 ID */
    private Long createdBy;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private Integer isDeleted;

    private LocalDateTime deletedAt;
}
