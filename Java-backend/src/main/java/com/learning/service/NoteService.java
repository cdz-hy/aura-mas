package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
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

    @Transactional
    public Note createNote(Long userId, NoteCreateRequest request) {
        Note note = new Note();
        note.setUserId(userId);
        note.setNoteName(request.getNoteName());
        note.setContent(request.getContent());
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

    public PageResult<Note> getUserNotes(Long userId, int page, int size) {
        Page<Note> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Note> wrapper = new LambdaQueryWrapper<Note>()
                .eq(Note::getUserId, userId)
                .orderByDesc(Note::getUpdatedAt);

        Page<Note> result = noteMapper.selectPage(pageParam, wrapper);
        return PageResult.of(result.getTotal(), page, size, result.getRecords());
    }

    @Transactional
    public Note updateNote(Long noteId, Long userId, NoteCreateRequest request) {
        Note note = getNoteById(noteId, userId);
        note.setNoteName(request.getNoteName());
        note.setContent(request.getContent());
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
    public void linkResource(Long noteId, Long resourceId, String selectedText, String positionInfo) {
        // 检查是否已存在关联
        NoteResourceRel existing = noteResourceRelMapper.selectOne(
                new LambdaQueryWrapper<NoteResourceRel>()
                        .eq(NoteResourceRel::getNoteId, noteId)
                        .eq(NoteResourceRel::getResourceId, resourceId));
        if (existing != null) {
            // 已存在则更新选中信息
            existing.setSelectedText(selectedText);
            existing.setPositionInfo(positionInfo);
            noteResourceRelMapper.updateById(existing);
            return;
        }
        NoteResourceRel rel = new NoteResourceRel();
        rel.setNoteId(noteId);
        rel.setResourceId(resourceId);
        rel.setSelectedText(selectedText);
        rel.setPositionInfo(positionInfo);
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
}
