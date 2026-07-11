package com.aura.mas.ui.components.charts

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.unit.dp
import com.aura.mas.ui.theme.Navy300
import com.aura.mas.ui.theme.Navy600
import kotlin.math.cos
import kotlin.math.sin

data class RadarData(
    val label: String,
    val value: Float, // 0.0 ~ 1.0
    val maxValue: Float = 1f
)

@Composable
fun RadarChart(
    data: List<RadarData>,
    modifier: Modifier = Modifier,
    fillColor: Color = Navy600.copy(alpha = 0.2f),
    strokeColor: Color = Navy600,
    gridColor: Color = MaterialTheme.colorScheme.outlineVariant
) {
    val textColor = MaterialTheme.colorScheme.onSurface

    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val center = Offset(size.width / 2, size.height / 2)
            val radius = minOf(size.width, size.height) / 2 * 0.7f
            val sides = data.size

            // Draw grid
            for (level in 1..5) {
                val r = radius * level / 5
                drawRadarGrid(center, r, sides, gridColor)
            }

            // Draw axes
            for (i in 0 until sides) {
                val angle = (2 * Math.PI * i / sides - Math.PI / 2).toFloat()
                val end = Offset(
                    center.x + radius * cos(angle),
                    center.y + radius * sin(angle)
                )
                drawLine(gridColor, center, end, strokeWidth = 1f)
            }

            // Draw data polygon
            val path = Path()
            data.forEachIndexed { index, item ->
                val angle = (2 * Math.PI * index / sides - Math.PI / 2).toFloat()
                val value = (item.value / item.maxValue).coerceIn(0f, 1f)
                val point = Offset(
                    center.x + radius * value * cos(angle),
                    center.y + radius * value * sin(angle)
                )
                if (index == 0) path.moveTo(point.x, point.y)
                else path.lineTo(point.x, point.y)
            }
            path.close()

            drawPath(path, fillColor)
            drawPath(path, strokeColor, style = Stroke(width = 2f))

            // Draw labels
            data.forEachIndexed { index, item ->
                val angle = (2 * Math.PI * index / sides - Math.PI / 2).toFloat()
                val labelRadius = radius + 30.dp.toPx()
                val labelX = center.x + labelRadius * cos(angle)
                val labelY = center.y + labelRadius * sin(angle)

                drawContext.canvas.nativeCanvas.drawText(
                    item.label,
                    labelX,
                    labelY + 4.dp.toPx(),
                    android.graphics.Paint().apply {
                        color = textColor.hashCode()
                        textSize = 10.dp.toPx()
                        textAlign = android.graphics.Paint.Align.CENTER
                    }
                )
            }
        }
    }
}

private fun DrawScope.drawRadarGrid(center: Offset, radius: Float, sides: Int, color: Color) {
    val path = Path()
    for (i in 0 until sides) {
        val angle = (2 * Math.PI * i / sides - Math.PI / 2).toFloat()
        val point = Offset(
            center.x + radius * cos(angle),
            center.y + radius * sin(angle)
        )
        if (i == 0) path.moveTo(point.x, point.y)
        else path.lineTo(point.x, point.y)
    }
    path.close()
    drawPath(path, color, style = Stroke(width = 1f))
}
