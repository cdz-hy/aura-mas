package com.learning.controller;

import com.learning.annotation.OperationLog;
import com.learning.common.OperationType;
import com.learning.common.Result;
import com.learning.security.JwtTokenProvider;
import com.learning.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@Tag(name = "Ticket管理")
@RestController
@RequestMapping("/api/ticket")
@RequiredArgsConstructor
public class TicketController {

    private final JwtTokenProvider jwtTokenProvider;
    private final UserService userService;

    @Operation(summary = "签发短期ticket(供Python SSE使用)")
    @OperationLog(type = OperationType.TICKET_ISSUE, module = "Ticket", desc = "签发临时票据")
    @PostMapping("/issue")
    public Result<Map<String, String>> issueTicket(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        String loginName = userService.getUserById(userId).getLoginName();
        String ticket = jwtTokenProvider.generateTicket(userId, loginName);

        Map<String, String> result = new HashMap<>();
        result.put("ticket", ticket);
        return Result.success(result);
    }
}
