package com.learning.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;

public class ServiceSecretFilter extends OncePerRequestFilter {

    private static final String INTERNAL_SECRET = "learning-system-internal-service-secret-2024";

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String path = request.getRequestURI();
        if (path.startsWith("/api/internal/")) {
            String secret = request.getHeader("X-Service-Secret");
            if (INTERNAL_SECRET.equals(secret)) {
                String userIdStr = request.getHeader("X-User-Id");
                Long userId = (userIdStr != null && !userIdStr.isEmpty()) ? Long.valueOf(userIdStr) : 0L;
                UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                        userId, null,
                        Collections.singletonList(new SimpleGrantedAuthority("ROLE_service")));
                SecurityContextHolder.getContext().setAuthentication(auth);
            } else {
                response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                response.setContentType("application/json;charset=UTF-8");
                response.getWriter().write("{\"code\":403,\"message\":\"Invalid service secret\"}");
                return;
            }
        }
        filterChain.doFilter(request, response);
    }
}
