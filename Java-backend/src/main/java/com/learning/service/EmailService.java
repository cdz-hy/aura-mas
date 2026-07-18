package com.learning.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.mail.*;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import java.util.Properties;

@Slf4j
@Service
public class EmailService {

    @Value("${mail.host:smtp.qq.com}")
    private String host;

    @Value("${mail.port:587}")
    private String port;

    @Value("${mail.username:}")
    private String username;

    @Value("${mail.password:}")
    private String password;

    @Value("${mail.from:}")
    private String from;

    /**
     * 发送验证码邮件
     */
    public void sendVerificationCode(String toEmail, String code) {
        Properties props = new Properties();
        props.put("mail.smtp.auth", "true");
        props.put("mail.smtp.starttls.enable", "true");
        props.put("mail.smtp.host", host);
        props.put("mail.smtp.port", port);
        props.put("mail.smtp.ssl.protocols", "TLSv1.2");

        Session session = Session.getInstance(props, new Authenticator() {
            @Override
            protected PasswordAuthentication getPasswordAuthentication() {
                return new PasswordAuthentication(username, password);
            }
        });

        try {
            MimeMessage message = new MimeMessage(session);
            message.setFrom(new InternetAddress(from));
            message.setRecipients(Message.RecipientType.TO, InternetAddress.parse(toEmail));
            message.setSubject("智学 - 邮箱验证码");

            String html = """
                <div style="font-family: 'Microsoft YaHei', sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                    <h2 style="color: #1a2847; margin-bottom: 16px;">智学 邮箱验证</h2>
                    <p style="color: #333; font-size: 15px; line-height: 1.6;">
                        你好！你正在注册智学学习平台账号，验证码如下：
                    </p>
                    <div style="background: #f0f3f9; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1a2847;">%s</span>
                    </div>
                    <p style="color: #666; font-size: 13px; line-height: 1.5;">
                        验证码 5 分钟内有效，请勿泄露给他人。<br/>
                        如果你没有注册智学账号，请忽略此邮件。
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
                    <p style="color: #999; font-size: 12px;">智学 · 个性化多智能体学习平台</p>
                </div>
                """.formatted(code);

            message.setContent(html, "text/html; charset=UTF-8");
            Transport.send(message);
            log.info("[邮件] 验证码已发送: to={}", toEmail);
        } catch (MessagingException e) {
            log.error("[邮件] 发送失败: to={}, error={}", toEmail, e.getMessage());
            throw new RuntimeException("邮件发送失败: " + e.getMessage());
        }
    }
}
