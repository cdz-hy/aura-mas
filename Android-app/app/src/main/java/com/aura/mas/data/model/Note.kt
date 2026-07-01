package com.aura.mas.data.model

import com.google.gson.annotations.SerializedName

data class Note(
    val id: Long = 0,
    @SerializedName("userId") val userId: Long = 0,
    @SerializedName("noteName") val noteName: String = "",
    val content: String = "",
    @SerializedName("isDeleted") val isDeleted: Int = 0,
    val createdAt: String? = null,
    val updatedAt: String? = null
)

data class NoteCreateRequest(
    @SerializedName("noteName") val noteName: String,
    val content: String = ""
)

data class NoteResourceRel(
    val id: Long = 0,
    @SerializedName("noteId") val noteId: Long = 0,
    @SerializedName("resourceId") val resourceId: Long = 0,
    @SerializedName("selectedText") val selectedText: String = "",
    @SerializedName("planId") val planId: Long? = null,
    @SerializedName("moduleName") val moduleName: String = "",
    @SerializedName("resourceTitle") val resourceTitle: String = ""
)
