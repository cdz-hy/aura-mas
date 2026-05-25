package com.learning.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.learning.common.ErrorCode;
import com.learning.common.Result;
import com.learning.security.JwtAuthenticationFilter;
import com.learning.security.ServiceSecretFilter;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                    JwtAuthenticationFilter jwtFilter,
                                                    ServiceSecretFilter serviceSecretFilter) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()
                // internal 端点：允许 service secret 或 admin JWT
                .requestMatchers("/api/internal/**").hasAnyRole("admin", "service")
                .requestMatchers("/api/token/internal/**").hasAnyRole("admin", "service")
                .requestMatchers("/api/plan/internal/**").hasAnyRole("admin", "service")
                .requestMatchers("/api/resource/internal/**").hasAnyRole("admin", "service")
                .requestMatchers("/api/quiz/internal/**").hasAnyRole("admin", "service")
                .requestMatchers("/api/task/internal/**").hasAnyRole("admin", "service")
                .requestMatchers("/api/admin/kb/internal/**").hasAnyRole("admin", "service")
                // admin 端点：仅 admin
                .requestMatchers("/api/admin/**").hasRole("admin")
                // 其他端点：需要登录
                .anyRequest().authenticated()
            )
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint((request, response, authException) -> {
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                    response.setCharacterEncoding("UTF-8");
                    response.getWriter().write(objectMapper.writeValueAsString(
                            Result.error(ErrorCode.UNAUTHORIZED.getCode(), "未登录或登录已过期")));
                })
                .accessDeniedHandler((request, response, accessDeniedException) -> {
                    response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                    response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                    response.setCharacterEncoding("UTF-8");
                    response.getWriter().write(objectMapper.writeValueAsString(
                            Result.error(ErrorCode.FORBIDDEN.getCode(), "权限不足")));
                })
            )
            .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
            .addFilterBefore(serviceSecretFilter, JwtAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
