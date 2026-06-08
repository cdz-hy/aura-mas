package com.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.learning.common.ErrorCode;
import com.learning.entity.Flashcard;
import com.learning.exception.BusinessException;
import com.learning.mapper.FlashcardMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class FlashcardService {

    private final FlashcardMapper flashcardMapper;

    public List<Flashcard> getByNoteId(Long noteId, Long userId) {
        return flashcardMapper.selectList(
                new LambdaQueryWrapper<Flashcard>()
                        .eq(Flashcard::getNoteId, noteId)
                        .eq(Flashcard::getUserId, userId)
                        .orderByAsc(Flashcard::getId));
    }

    public List<Flashcard> getDueCards(Long userId, int limit) {
        return flashcardMapper.selectList(
                new LambdaQueryWrapper<Flashcard>()
                        .eq(Flashcard::getUserId, userId)
                        .le(Flashcard::getNextReviewAt, LocalDateTime.now())
                        .orderByAsc(Flashcard::getNextReviewAt)
                        .last("LIMIT " + limit));
    }

    @Transactional
    public void saveFlashcards(Long noteId, Long userId, List<Flashcard> cards) {
        for (Flashcard card : cards) {
            card.setNoteId(noteId);
            card.setUserId(userId);
            card.setEaseFactor(2.5);
            card.setReviewInterval(0);
            card.setReviewCount(0);
            card.setNextReviewAt(LocalDateTime.now());
            card.setCreatedAt(LocalDateTime.now());
            flashcardMapper.insert(card);
        }
    }

    /**
     * SM-2 间隔复习算法
     * @param quality 用户评分 1-5 (1=忘了, 2=困难, 3=还行, 4=较容易, 5=很简单)
     */
    @Transactional
    public Flashcard reviewCard(Long cardId, Long userId, int quality) {
        Flashcard card = flashcardMapper.selectById(cardId);
        if (card == null || !card.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FLASHCARD_NOT_FOUND);
        }

        double ef = card.getEaseFactor();
        int interval = card.getReviewInterval();
        int count = card.getReviewCount();

        // SM-2 核心公式
        ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
        if (ef < 1.3) ef = 1.3;

        if (quality < 3) {
            // 忘了或太难：重置间隔
            interval = 1;
            count = 0;
        } else {
            count++;
            if (count == 1) {
                interval = 1;
            } else if (count == 2) {
                interval = 6;
            } else {
                interval = (int) Math.round(interval * ef);
            }
        }

        card.setEaseFactor(ef);
        card.setReviewInterval(interval);
        card.setReviewCount(count);
        card.setNextReviewAt(LocalDateTime.now().plusDays(interval));
        flashcardMapper.updateById(card);
        return card;
    }

    @Transactional
    public void deleteByNoteId(Long noteId, Long userId) {
        flashcardMapper.delete(
                new LambdaQueryWrapper<Flashcard>()
                        .eq(Flashcard::getNoteId, noteId)
                        .eq(Flashcard::getUserId, userId));
    }

    @Transactional
    public void deleteCard(Long cardId, Long userId) {
        Flashcard card = flashcardMapper.selectById(cardId);
        if (card != null && card.getUserId().equals(userId)) {
            flashcardMapper.deleteById(cardId);
        }
    }

    public long countDueCards(Long userId) {
        return flashcardMapper.selectCount(
                new LambdaQueryWrapper<Flashcard>()
                        .eq(Flashcard::getUserId, userId)
                        .le(Flashcard::getNextReviewAt, LocalDateTime.now()));
    }
}
