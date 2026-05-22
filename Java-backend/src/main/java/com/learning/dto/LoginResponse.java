package com.learning.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class LoginResponse {

    private String token;
    private LoginResponse.UserDTO user;
    private List<MenuNode> menus;

    @Data
    @Builder
    public static class UserDTO {
        private Long id;
        private String loginName;
        private String nickname;
        private String email;
        private String avatarUrl;
        private String role;
    }
}
