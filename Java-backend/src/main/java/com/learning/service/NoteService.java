package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.common.ErrorCode;
import com.learning.common.PageResult;
import com.learning.dto.NoteCreateRequest;
import com.learning.entity.Note;
import com.learning.entity.NoteResourceRel;
import com.learning.exception.BusinessException;
import com.learning.mapper.NoteMapper;
import com.learning.mapper.NoteResourceRelMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class NoteService {

    private final NoteMapper noteMapper;
    private final NoteResourceRelMapper noteResourceRelMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Transactional
    public Note createNote(Long userId, NoteCreateRequest request) {
        Note note = new Note();
        note.setUserId(userId);
        note.setNoteName(request.getNoteName());
        note.setContent(request.getContent());
        note.setTags(serializeTags(request.getTags()));
        note.setIsPinned(request.getIsPinned() != null ? request.getIsPinned() : 0);
        applyCaptureMetadata(note, request);
        note.setCreatedAt(LocalDateTime.now());
        note.setUpdatedAt(LocalDateTime.now());
        noteMapper.insert(note);
        return note;
    }

    public Note getNoteById(Long noteId, Long userId) {
        Note note = noteMapper.selectById(noteId);
        if (note == null || !note.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        return note;
    }

    public Note getNoteById(Long noteId) {
        Note note = noteMapper.selectById(noteId);
        if (note == null) {
            throw new BusinessException(ErrorCode.NOTE_NOT_FOUND);
        }
        return note;
    }

    public PageResult<Note> getUserNotes(Long userId, int page, int size, String keyword) {
        Page<Note> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Note> wrapper = new LambdaQueryWrapper<Note>()
                .eq(Note::getUserId, userId);

        if (keyword != null && !keyword.isBlank()) {
            wrapper.and(w -> w
                    .like(Note::getNoteName, keyword)
                    .or()
                    .like(Note::getContent, keyword));
        }

        wrapper.orderByDesc(Note::getIsPinned)
                .orderByDesc(Note::getUpdatedAt);

        Page<Note> result = noteMapper.selectPage(pageParam, wrapper);
        return PageResult.of(result.getTotal(), page, size, result.getRecords());
    }

    @Transactional
    public Note updateNote(Long noteId, Long userId, NoteCreateRequest request) {
        Note note = getNoteById(noteId, userId);
        note.setNoteName(request.getNoteName());
        note.setContent(request.getContent());
        if (request.getTags() != null) {
            note.setTags(serializeTags(request.getTags()));
        }
        if (request.getIsPinned() != null) {
            note.setIsPinned(request.getIsPinned());
        }
        applyCaptureMetadata(note, request);
        note.setUpdatedAt(LocalDateTime.now());
        noteMapper.updateById(note);
        return note;
    }

    @Transactional
    public void deleteNote(Long noteId, Long userId) {
        getNoteById(noteId, userId);
        noteMapper.deleteById(noteId);
        noteResourceRelMapper.delete(
                new LambdaQueryWrapper<NoteResourceRel>().eq(NoteResourceRel::getNoteId, noteId));
    }

    @Transactional
    public void linkResource(Long noteId, Long resourceId, String selectedText, String positionInfo,
                             Long planId, String moduleName, String resourceTitle) {
        // 检查是否已存在关联
        NoteResourceRel existing = noteResourceRelMapper.selectOne(
                new LambdaQueryWrapper<NoteResourceRel>()
                        .eq(NoteResourceRel::getNoteId, noteId)
                        .eq(NoteResourceRel::getResourceId, resourceId));
        if (existing != null) {
            existing.setSelectedText(selectedText);
            existing.setPositionInfo(positionInfo);
            existing.setPlanId(planId);
            existing.setModuleName(moduleName);
            existing.setResourceTitle(resourceTitle);
            noteResourceRelMapper.updateById(existing);
            return;
        }
        NoteResourceRel rel = new NoteResourceRel();
        rel.setNoteId(noteId);
        rel.setResourceId(resourceId);
        rel.setSelectedText(selectedText);
        rel.setPositionInfo(positionInfo);
        rel.setPlanId(planId);
        rel.setModuleName(moduleName);
        rel.setResourceTitle(resourceTitle);
        noteResourceRelMapper.insert(rel);
    }

    @Transactional
    public void unlinkResource(Long noteId, Long resourceId) {
        noteResourceRelMapper.delete(
                new LambdaQueryWrapper<NoteResourceRel>()
                        .eq(NoteResourceRel::getNoteId, noteId)
                        .eq(NoteResourceRel::getResourceId, resourceId));
    }

    public List<NoteResourceRel> getNoteResourceRels(Long noteId) {
        return noteResourceRelMapper.selectList(
                new LambdaQueryWrapper<NoteResourceRel>().eq(NoteResourceRel::getNoteId, noteId));
    }

    private void applyCaptureMetadata(Note note, NoteCreateRequest request) {
        if (request.getNoteType() != null) {
            note.setNoteType(request.getNoteType());
        }
        if (request.getOrganizeStatus() != null) {
            note.setOrganizeStatus(request.getOrganizeStatus());
        }
        if (request.getSourceType() != null) {
            note.setSourceType(request.getSourceType());
        }
        if (request.getSourceId() != null) {
            note.setSourceId(request.getSourceId());
        }
        if (request.getSourceTitle() != null) {
            note.setSourceTitle(request.getSourceTitle());
        }
        if (request.getSourceRoute() != null) {
            note.setSourceRoute(request.getSourceRoute());
        }
        if (request.getExcerpt() != null) {
            note.setExcerpt(request.getExcerpt());
        }
    }

    private String serializeTags(List<String> tags) {
        if (tags == null) return null;
        try {
            return objectMapper.writeValueAsString(tags);
        } catch (JsonProcessingException e) {
            return "[]";
        }
    }
}
