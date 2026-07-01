package com.aura.mas.ui.quiz

import androidx.compose.animation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aura.mas.data.model.QuizQuestion
import com.aura.mas.ui.theme.*

@Composable
fun QuizQuestionView(
    question: QuizQuestion,
    questionIndex: Int,
    totalQuestions: Int,
    selectedAnswer: String?,
    onAnswer: (String) -> Unit,
    onNext: () -> Unit,
    onPrev: () -> Unit,
    onSubmit: () -> Unit,
    isSubmitting: Boolean,
    showResult: Boolean = false,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxWidth()) {
        // Progress
        LinearProgressIndicator(
            progress = { (questionIndex + 1).toFloat() / totalQuestions },
            modifier = Modifier.fillMaxWidth(),
            trackColor = MaterialTheme.colorScheme.surfaceVariant
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "第 ${questionIndex + 1} / $totalQuestions 题",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(16.dp))

        // Question type badge
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = MaterialTheme.colorScheme.tertiaryContainer
        ) {
            Text(
                getQuestionTypeName(question.questionType),
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onTertiaryContainer
            )
        }

        Spacer(Modifier.height(12.dp))

        // Question text
        Text(
            question.questionText,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(Modifier.height(16.dp))

        // Answer options based on type
        when (question.questionType) {
            QuizQuestion.TYPE_SINGLE_CHOICE, QuizQuestion.TYPE_TRUE_FALSE -> {
                SingleChoiceOptions(question, selectedAnswer, onAnswer, showResult)
            }
            QuizQuestion.TYPE_MULTIPLE_CHOICE -> {
                MultipleChoiceOptions(question, selectedAnswer, onAnswer, showResult)
            }
            QuizQuestion.TYPE_FILL_BLANK, QuizQuestion.TYPE_SHORT_ANSWER, QuizQuestion.TYPE_CODE_OUTPUT -> {
                TextInputAnswer(question, selectedAnswer, onAnswer, showResult)
            }
        }

        // Result feedback
        if (showResult) {
            Spacer(Modifier.height(16.dp))
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(
                    containerColor = if (question.isCorrect == true) MaterialTheme.colorScheme.secondaryContainer
                    else MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Column(Modifier.padding(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            if (question.isCorrect == true) Icons.Default.CheckCircle else Icons.Default.Cancel,
                            null,
                            tint = if (question.isCorrect == true) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.error
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            if (question.isCorrect == true) "回答正确！" else "回答错误",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                    if (question.feedback.isNotBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Text(question.feedback, style = MaterialTheme.typography.bodySmall)
                    }
                    if (question.isCorrect != true && question.correctAnswer.isNotBlank()) {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "正确答案: ${question.correctAnswer}",
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.secondary
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(24.dp))

        // Navigation
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            OutlinedButton(
                onClick = onPrev,
                enabled = questionIndex > 0,
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(4.dp))
                Text("上一题")
            }

            if (questionIndex == totalQuestions - 1) {
                Button(
                    onClick = onSubmit,
                    enabled = !isSubmitting && selectedAnswer != null,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    if (isSubmitting) {
                        CircularProgressIndicator(Modifier.size(18.dp), color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
                    } else {
                        Text("提交答案")
                    }
                }
            } else {
                Button(
                    onClick = onNext,
                    enabled = selectedAnswer != null,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("下一题")
                    Spacer(Modifier.width(4.dp))
                    Icon(Icons.Default.ArrowForward, null, modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

@Composable
private fun SingleChoiceOptions(
    question: QuizQuestion,
    selectedAnswer: String?,
    onAnswer: (String) -> Unit,
    showResult: Boolean
) {
    val options = question.options ?: listOf("A", "B", "C", "D")
    options.forEach { option ->
        val isSelected = selectedAnswer == option
        val isCorrect = showResult && option == question.correctAnswer
        val isWrong = showResult && isSelected && option != question.correctAnswer

        Card(
            onClick = { if (!showResult) onAnswer(option) },
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(
                containerColor = when {
                    isCorrect -> MaterialTheme.colorScheme.secondaryContainer
                    isWrong -> MaterialTheme.colorScheme.errorContainer
                    isSelected -> MaterialTheme.colorScheme.primaryContainer
                    else -> MaterialTheme.colorScheme.surface
                }
            ),
            elevation = CardDefaults.cardElevation(
                defaultElevation = if (isSelected) 2.dp else 0.5.dp
            )
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                RadioButton(
                    selected = isSelected,
                    onClick = { if (!showResult) onAnswer(option) },
                    enabled = !showResult
                )
                Spacer(Modifier.width(8.dp))
                Text(option, style = MaterialTheme.typography.bodyMedium)
                if (isCorrect) {
                    Spacer(Modifier.weight(1f))
                    Icon(Icons.Default.CheckCircle, null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(20.dp))
                }
                if (isWrong) {
                    Spacer(Modifier.weight(1f))
                    Icon(Icons.Default.Cancel, null, tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(20.dp))
                }
            }
        }
    }
}

@Composable
private fun MultipleChoiceOptions(
    question: QuizQuestion,
    selectedAnswer: String?,
    onAnswer: (String) -> Unit,
    showResult: Boolean
) {
    val options = question.options ?: listOf("A", "B", "C", "D")
    val selectedSet = selectedAnswer?.split(",")?.toSet() ?: emptySet()

    options.forEach { option ->
        val isSelected = selectedSet.contains(option)
        Card(
            onClick = {
                if (!showResult) {
                    val newSet = if (isSelected) selectedSet - option else selectedSet + option
                    onAnswer(newSet.joinToString(","))
                }
            },
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(
                containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer
                else MaterialTheme.colorScheme.surface
            )
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Checkbox(
                    checked = isSelected,
                    onCheckedChange = { checked ->
                        if (!showResult) {
                            val newSet = if (checked) selectedSet + option else selectedSet - option
                            onAnswer(newSet.joinToString(","))
                        }
                    },
                    enabled = !showResult
                )
                Spacer(Modifier.width(8.dp))
                Text(option, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun TextInputAnswer(
    question: QuizQuestion,
    selectedAnswer: String?,
    onAnswer: (String) -> Unit,
    showResult: Boolean
) {
    OutlinedTextField(
        value = selectedAnswer ?: "",
        onValueChange = { if (!showResult) onAnswer(it) },
        label = { Text(when (question.questionType) {
            QuizQuestion.TYPE_FILL_BLANK -> "填入答案"
            QuizQuestion.TYPE_CODE_OUTPUT -> "输出结果"
            else -> "输入你的答案"
        }) },
        modifier = Modifier.fillMaxWidth(),
        minLines = if (question.questionType == QuizQuestion.TYPE_CODE_OUTPUT) 4 else 2,
        maxLines = 8,
        shape = RoundedCornerShape(12.dp),
        readOnly = showResult
    )
}

private fun getQuestionTypeName(type: String) = when (type) {
    QuizQuestion.TYPE_SINGLE_CHOICE -> "单选题"
    QuizQuestion.TYPE_MULTIPLE_CHOICE -> "多选题"
    QuizQuestion.TYPE_TRUE_FALSE -> "判断题"
    QuizQuestion.TYPE_FILL_BLANK -> "填空题"
    QuizQuestion.TYPE_SHORT_ANSWER -> "简答题"
    QuizQuestion.TYPE_CODE_OUTPUT -> "代码输出"
    else -> "题目"
}
