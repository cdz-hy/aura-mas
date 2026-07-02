package com.aura.mas.ui.chat

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aura.mas.data.model.ThinkingStep

@Composable
fun ThinkingProcess(
    thinkings: List<ThinkingStep>,
    isStreaming: Boolean = false,
    modifier: Modifier = Modifier
) {
    if (thinkings.isEmpty() && !isStreaming) return

    var isExpanded by remember { mutableStateOf(isStreaming) }

    // Auto-expand when streaming starts
    LaunchedEffect(isStreaming) {
        if (isStreaming) isExpanded = true
    }

    Column(modifier = modifier) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { isExpanded = !isExpanded }
                .padding(vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Default.ExpandMore,
                null,
                modifier = Modifier.size(18.dp)
                    .animateContentSize(),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.width(8.dp))
            Text(
                "思考过程",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (thinkings.isNotEmpty()) {
                Spacer(Modifier.width(8.dp))
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Text(
                        "${thinkings.size} 步",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        style = MaterialTheme.typography.labelSmall
                    )
                }
            }
            if (isStreaming) {
                Spacer(Modifier.width(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        Modifier.size(6.dp).clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primary)
                    )
                    Spacer(Modifier.width(4.dp))
                    Text(
                        "正在思考",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }

        // Expanded content
        AnimatedVisibility(
            visible = isExpanded,
            enter = expandVertically(),
            exit = shrinkVertically()
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(start = 8.dp, top = 8.dp)
            ) {
                thinkings.forEachIndexed { index, step ->
                    ThinkingStepItem(
                        step = step,
                        isLast = index == thinkings.size - 1,
                        isStreaming = isStreaming && index == thinkings.size - 1
                    )
                }

                // Streaming indicator
                if (isStreaming && (thinkings.isEmpty() || thinkings.last().content.isNotBlank())) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            Modifier.size(8.dp).clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary)
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "正在分析...",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ThinkingStepItem(
    step: ThinkingStep,
    isLast: Boolean,
    isStreaming: Boolean
) {
    Row(modifier = Modifier.padding(bottom = 8.dp)) {
        // Timeline dot and line
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                Modifier.size(8.dp).clip(CircleShape)
                    .background(
                        if (isLast && isStreaming) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.outline
                    )
            )
            if (!isLast) {
                Box(
                    Modifier.width(2.dp).height(24.dp)
                        .background(MaterialTheme.colorScheme.outline.copy(alpha = 0.3f))
                )
            }
        }
        Spacer(Modifier.width(12.dp))

        // Content
        Column {
            Text(
                step.agent,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Medium
            )
            if (step.content.isNotBlank()) {
                Text(
                    step.content,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
