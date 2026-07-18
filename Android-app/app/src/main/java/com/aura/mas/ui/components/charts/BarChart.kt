package com.aura.mas.ui.components.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.aura.mas.ui.theme.Sage500

data class BarData(
    val label: String,
    val value: Float,
    val maxValue: Float = 1f,
    val color: Color = Sage500,
    val displayValue: String = ""
)

@Composable
fun HorizontalBarChart(
    data: List<BarData>,
    modifier: Modifier = Modifier,
    barHeight: Int = 10,
    animate: Boolean = true
) {
    Column(modifier = modifier) {
        data.forEach { item ->
            val fraction = if (item.maxValue > 0) (item.value / item.maxValue).coerceIn(0f, 1f) else 0f
            val animatedFraction by animateFloatAsState(
                targetValue = fraction,
                animationSpec = tween(600),
                label = "bar"
            )

            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    item.label,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.width(28.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.width(8.dp))
                Box(modifier = Modifier.weight(1f).height(barHeight.dp)) {
                    Box(
                        modifier = Modifier.fillMaxSize()
                            .clip(RoundedCornerShape((barHeight / 2).dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant)
                    )
                    Box(
                        modifier = Modifier.fillMaxHeight()
                            .fillMaxWidth(if (animate) animatedFraction else fraction)
                            .clip(RoundedCornerShape((barHeight / 2).dp))
                            .background(item.color)
                    )
                }
                Spacer(Modifier.width(8.dp))
                Text(
                    item.displayValue.ifEmpty { "${item.value.toInt()}" },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.width(40.dp)
                )
            }
        }
    }
}

@Composable
fun VerticalBarChart(
    data: List<BarData>,
    modifier: Modifier = Modifier,
    animate: Boolean = true,
    maxHeight: Int = 120
) {
    val maxVal = data.maxOfOrNull { it.value } ?: 1f

    Row(
        modifier = modifier.height(maxHeight.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.Bottom
    ) {
        data.forEach { item ->
            val fraction = if (maxVal > 0) (item.value / maxVal).coerceIn(0f, 1f) else 0f
            val animatedFraction by animateFloatAsState(
                targetValue = fraction,
                animationSpec = tween(600),
                label = "bar"
            )

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Bottom,
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    item.displayValue.ifEmpty { "${item.value.toInt()}" },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(4.dp))
                Box(
                    modifier = Modifier.width(24.dp)
                        .fillMaxHeight(if (animate) animatedFraction else fraction)
                        .clip(RoundedCornerShape(topStart = 6.dp, topEnd = 6.dp))
                        .background(item.color)
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    item.label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
