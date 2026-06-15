package com.learning.controller;

import com.learning.common.Result;
import com.learning.entity.ResourceGenerationTask;
import com.learning.service.LearningResourceService;
import com.learning.service.TaskDispatchService;
import com.learning.service.TaskSseService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TaskControllerTest {

    @Test
    void internalCreateOnlyCreatesTaskRecordWithoutDispatchingMq() {
        TaskDispatchService taskDispatchService = mock(TaskDispatchService.class);
        LearningResourceService resourceService = mock(LearningResourceService.class);
        TaskSseService taskSseService = mock(TaskSseService.class);
        TaskController controller = new TaskController(
                taskDispatchService,
                resourceService,
                taskSseService,
                new ObjectMapper()
        );

        ResourceGenerationTask task = new ResourceGenerationTask();
        task.setId(37L);
        task.setPlanId(14L);
        task.setResourceId(57L);
        task.setTaskStatus(1);
        task.setAgentChain("animation");

        when(taskDispatchService.createInternalTask(14L, 57L, "animation")).thenReturn(task);

        Result<ResourceGenerationTask> result = controller.createTaskInternal(Map.of(
                "planId", 14,
                "resourceId", 57,
                "agentChain", "animation"
        ));

        assertEquals(37L, result.getData().getId());
        assertEquals(1, result.getData().getTaskStatus());
        verify(taskDispatchService).createInternalTask(14L, 57L, "animation");
        verify(taskDispatchService, never()).dispatchTask(14L, 57L, "animation");
    }

    @Test
    void internalUpdateCanSkipSourceResourceStatusUpdate() {
        TaskDispatchService taskDispatchService = mock(TaskDispatchService.class);
        LearningResourceService resourceService = mock(LearningResourceService.class);
        TaskSseService taskSseService = mock(TaskSseService.class);
        TaskController controller = new TaskController(
                taskDispatchService,
                resourceService,
                taskSseService,
                new ObjectMapper()
        );

        controller.updateTaskInternal(37L, Map.of(
                "taskStatus", 2,
                "updateResourceStatus", false
        ));

        verify(taskDispatchService).updateTaskStatus(37L, 2, false);
    }
}
