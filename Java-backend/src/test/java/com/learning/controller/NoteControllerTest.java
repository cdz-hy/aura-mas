package com.learning.controller;

import com.learning.common.Result;
import com.learning.dto.NoteCreateRequest;
import com.learning.entity.Note;
import com.learning.mapper.NoteMapper;
import com.learning.mapper.NoteResourceRelMapper;
import com.learning.service.NoteService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.core.Authentication;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class NoteControllerTest {

    @Test
    void createNotePersistsCaptureMetadata() {
        NoteMapper noteMapper = mock(NoteMapper.class);
        NoteService noteService = new NoteService(noteMapper, mock(NoteResourceRelMapper.class));
        NoteController controller = new NoteController(noteService);
        Authentication authentication = mock(Authentication.class);
        when(authentication.getPrincipal()).thenReturn(42L);
        when(noteMapper.insert(any(Note.class))).thenAnswer(invocation -> {
            Note note = invocation.getArgument(0);
            note.setId(9L);
            return 1;
        });

        NoteCreateRequest request = new NoteCreateRequest();
        request.setNoteName("无标题笔记");
        request.setContent("我的理解");
        request.setNoteType("excerpt");
        request.setOrganizeStatus("pending");
        request.setSourceType("resource");
        request.setSourceId(12L);
        request.setSourceTitle("极限的定义");
        request.setSourceRoute("/plans/1/resources/12");
        request.setExcerpt("当 x 趋近于 a 时");

        Result<Note> result = controller.createNote(authentication, request);

        ArgumentCaptor<Note> captor = ArgumentCaptor.forClass(Note.class);
        verify(noteMapper).insert(captor.capture());
        Note persisted = captor.getValue();
        assertEquals(42L, persisted.getUserId());
        assertEquals("excerpt", persisted.getNoteType());
        assertEquals("pending", persisted.getOrganizeStatus());
        assertEquals("resource", persisted.getSourceType());
        assertEquals(12L, persisted.getSourceId());
        assertEquals("极限的定义", persisted.getSourceTitle());
        assertEquals("/plans/1/resources/12", persisted.getSourceRoute());
        assertEquals("当 x 趋近于 a 时", persisted.getExcerpt());
        assertEquals(9L, result.getData().getId());
    }

    @Test
    void createNoteAllowsEmptyExcerptAndLegacyPayload() {
        NoteMapper noteMapper = mock(NoteMapper.class);
        NoteService noteService = new NoteService(noteMapper, mock(NoteResourceRelMapper.class));
        NoteController controller = new NoteController(noteService);
        Authentication authentication = mock(Authentication.class);
        when(authentication.getPrincipal()).thenReturn(7L);
        when(noteMapper.insert(any(Note.class))).thenReturn(1);

        NoteCreateRequest request = new NoteCreateRequest();
        request.setNoteName("旧笔记");
        request.setContent("只有标题和内容");
        request.setExcerpt("");

        controller.createNote(authentication, request);

        ArgumentCaptor<Note> captor = ArgumentCaptor.forClass(Note.class);
        verify(noteMapper).insert(captor.capture());
        Note persisted = captor.getValue();
        assertEquals("旧笔记", persisted.getNoteName());
        assertEquals("", persisted.getExcerpt());
        assertNull(persisted.getNoteType());
        assertNull(persisted.getOrganizeStatus());
        assertNull(persisted.getSourceType());
    }

    @Test
    void updateNotePersistsOrganizeStatus() {
        NoteMapper noteMapper = mock(NoteMapper.class);
        NoteService noteService = new NoteService(noteMapper, mock(NoteResourceRelMapper.class));
        NoteController controller = new NoteController(noteService);
        Authentication authentication = mock(Authentication.class);
        when(authentication.getPrincipal()).thenReturn(42L);

        Note existing = new Note();
        existing.setId(3L);
        existing.setUserId(42L);
        existing.setNoteName("草稿");
        existing.setContent("原文");
        existing.setNoteType("question");
        existing.setOrganizeStatus("pending");
        when(noteMapper.selectById(3L)).thenReturn(existing);

        NoteCreateRequest request = new NoteCreateRequest();
        request.setNoteName("整理后");
        request.setContent("整理内容");
        request.setNoteType("question");
        request.setOrganizeStatus("organized");

        Result<Note> result = controller.updateNote(authentication, 3L, request);

        ArgumentCaptor<Note> captor = ArgumentCaptor.forClass(Note.class);
        verify(noteMapper).updateById(captor.capture());
        assertEquals("organized", captor.getValue().getOrganizeStatus());
        assertEquals("question", captor.getValue().getNoteType());
        assertEquals("整理后", result.getData().getNoteName());
    }
}
