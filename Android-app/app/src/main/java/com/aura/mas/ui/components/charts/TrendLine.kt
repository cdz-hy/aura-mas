package com.aura.mas.ui.components.charts

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import com.aura.mas.ui.theme.Navy600
import com.aura.mas.ui.theme.Navy600

data class TrendPoint(val label: String, val value: Float)

@Composable
fun TrendLineChart(
    data: List<TrendPoint>,
    modifier: Modifier = Modifier,
    lineColor: androidx.compose.ui.graphics.Color = Navy600
) {
    if (data.isEmpty()) return

    val maxVal = data.maxOf { it.value }.coerceAtLeast(1f)
    val minVal = data.minOf { it.value }
    val range = (maxVal - minVal).coerceAtLeast(1f)

    Canvas(modifier = modifier.fillMaxSize()) {
        val width = size.width
        val height = size.height
        val padding = 16f
        val chartWidth = width - padding * 2
        val chartHeight = height - padding * 2

        val path = Path()
        val fillPath = Path()

        data.forEachIndexed { index, point ->
            val x = padding + chartWidth * index / (data.size - 1).coerceAtLeast(1)
            val y = padding + chartHeight * (1 - (point.value - minVal) / range)

            if (index == 0) {
                path.moveTo(x, y)
                fillPath.moveTo(x, height)
                fillPath.lineTo(x, y)
            } else {
                // Smooth curve
                val prevX = padding + chartWidth * (index - 1) / (data.size - 1).coerceAtLeast(1)
                val prevPoint = data[index - 1]
                val prevY = padding + chartHeight * (1 - (prevPoint.value - minVal) / range)
                val midX = (prevX + x) / 2

                path.cubicTo(midX, prevY, midX, y, x, y)
                fillPath.cubicTo(midX, prevY, midX, y, x, y)
            }
        }

        fillPath.lineTo(padding + chartWidth, height)
        fillPath.close()

        // Fill gradient
        drawPath(
            fillPath,
            Brush.verticalGradient(
                colors = listOf(lineColor.copy(alpha = 0.3f), lineColor.copy(alpha = 0f)),
                startY = 0f,
                endY = height
            )
        )

        // Line
        drawPath(
            path,
            lineColor,
            style = Stroke(width = 3f, cap = StrokeCap.Round, join = StrokeJoin.Round)
        )

        // Dots
        data.forEachIndexed { index, point ->
            val x = padding + chartWidth * index / (data.size - 1).coerceAtLeast(1)
            val y = padding + chartHeight * (1 - (point.value - minVal) / range)
            drawCircle(lineColor, 4f, Offset(x, y))
            drawCircle(androidx.compose.ui.graphics.Color.White, 2.5f, Offset(x, y))
        }
    }
}
