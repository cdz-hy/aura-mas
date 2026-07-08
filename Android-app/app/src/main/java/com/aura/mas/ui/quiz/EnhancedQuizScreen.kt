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

/**
 * Format correct answer for display. Handles arrays, indices, letters, and plain text.
 */
private fun formatCorrectAnswer(question: QuizQuestion): String {
    val raw = question.correctAnswer ?: return ""
    val indices = question.getCorrectIndices()
    if (indices.isEmpty()) {
        val str = raw.toString()
        if (str == "null" || str.isBlank()) return ""
        return str
    }
    val options = question.getOptionsOrDefault()
    return indices.sorted().joinToString("、") { idx ->
        if (idx in options.indices) options[idx] else idx.toString()
    }
}

@Composable
fun QuizQuestionView(
    question: QuizQuestion,
    questionIndex: Int,
    totalQuestions: Int,
    selectedAnswer: Any?,
    onAnswer: (Any) -> Unit,
    onNext: () -> Unit,
    onPrev: () -> Unit,
    onSubmit: () -> Unit,
    isSubmitting: Boolean,
    showResult: Boolean = false,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    // Reset scroll position when switching questions
    LaunchedEffect(questionIndex) {
        scrollState.scrollTo(0)
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .verticalScroll(scrollState)
    ) {
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
                        if (question.perQuestionScore != null) {
                            Spacer(Modifier.weight(1f))
                            Text(
                                "${(question.perQuestionScore!! * 100).toInt()}分",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                    if (question.feedback.isNotBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Text(question.feedback, style = MaterialTheme.typography.bodySmall)
                    }
                    val correctAnsStr = formatCorrectAnswer(question)
                    if (question.isCorrect != true && correctAnsStr.isNotBlank()) {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "正确答案: $correctAnsStr",
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.secondary
                        )
                    }
                    // Grading details
                    if (!question.keyPointsHit.isNullOrEmpty()) {
                        Spacer(Modifier.height(8.dp))
                        Text("掌握的知识点:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
                        question.keyPointsHit!!.forEach { point ->
                            Text("  · $point", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
                        }
                    }
                    if (!question.keyPointsMissed.isNullOrEmpty()) {
                        Spacer(Modifier.height(4.dp))
                        Text("未掌握的知识点:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
                        question.keyPointsMissed!!.forEach { point ->
                            Text("  · $point", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                        }
                    }
                    if (!question.improvementSuggestions.isNullOrEmpty()) {
                        Spacer(Modifier.height(4.dp))
                        Text("改进建议:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
                        question.improvementSuggestions!!.forEach { suggestion ->
                            Text("  · $suggestion", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                    if (question.explanation.isNotBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Text("解析:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
                        Text(question.explanation, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }

        Spacer(Modifier.height(24.dp))

        // Navigation
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
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
    selectedAnswer: Any?,
    onAnswer: (Any) -> Unit,
    showResult: Boolean
) {
    val options = question.getOptionsOrDefault().ifEmpty { listOf("A", "B", "C", "D") }
    val correctIndices = question.getCorrectIndices()
    val selectedIndex = when (selectedAnswer) {
        is Number -> selectedAnswer.toInt()
        is String -> selectedAnswer.toIntOrNull() ?: options.indexOf(selectedAnswer)
        else -> -1
    }

    options.forEachIndexed { index, option ->
        val isSelected = selectedIndex == index
        val isCorrect = showResult && index in correctIndices
        val isWrong = showResult && isSelected && !isCorrect

        Card(
            onClick = { if (!showResult) onAnswer(index) },
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
                    onClick = { if (!showResult) onAnswer(index) },
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
    selectedAnswer: Any?,
    onAnswer: (Any) -> Unit,
    showResult: Boolean
) {
    val options = question.getOptionsOrDefault().ifEmpty { listOf("A", "B", "C", "D") }
    val correctIndices = question.getCorrectIndices()
    val selectedIndices = remember(selectedAnswer) {
        when (selectedAnswer) {
            is List<*> -> selectedAnswer.mapNotNull { (it as? Number)?.toInt() }.toSet()
            is String -> {
                selectedAnswer.split(",")
                    .mapNotNull { it.trim().toIntOrNull() ?: options.indexOf(it).takeIf { idx -> idx >= 0 } }
                    .toSet()
            }
            else -> emptySet()
        }
    }

    options.forEachIndexed { index, option ->
        val isSelected = selectedIndices.contains(index)
        val isCorrect = showResult && index in correctIndices
        val isWrong = showResult && isSelected && !isCorrect
        Card(
            onClick = {
                if (!showResult) {
                    val newSet = if (isSelected) selectedIndices - index else selectedIndices + index
                    onAnswer(newSet.toList().sorted())
                }
            },
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(
                containerColor = when {
                    isCorrect -> MaterialTheme.colorScheme.secondaryContainer
                    isWrong -> MaterialTheme.colorScheme.errorContainer
                    isSelected -> MaterialTheme.colorScheme.primaryContainer
                    else -> MaterialTheme.colorScheme.surface
                }
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
                            val newSet = if (checked) selectedIndices + index else selectedIndices - index
                            onAnswer(newSet.toList().sorted())
                        }
                    },
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
private fun TextInputAnswer(
    question: QuizQuestion,
    selectedAnswer: Any?,
    onAnswer: (Any) -> Unit,
    showResult: Boolean
) {
    val text = (selectedAnswer as? String) ?: ""
    OutlinedTextField(
        value = text,
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
