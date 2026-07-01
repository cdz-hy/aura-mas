package com.aura.mas.ui.components.graph

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.aura.mas.ui.theme.*
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

data class GraphNode(
    val id: Long,
    val label: String,
    val mastery: Float = 0.5f,
    val importance: Float = 0.5f,
    var x: Float = 0f,
    var y: Float = 0f
)

data class GraphEdge(
    val sourceId: Long,
    val targetId: Long,
    val weight: Float = 1f
)

@Composable
fun KnowledgeGraphView(
    nodes: List<GraphNode>,
    edges: List<GraphEdge>,
    modifier: Modifier = Modifier
) {
    var scale by remember { mutableFloatStateOf(1f) }
    var offsetX by remember { mutableFloatStateOf(0f) }
    var offsetY by remember { mutableFloatStateOf(0f) }

    // Force-directed layout simulation
    val positionedNodes = remember(nodes, edges) {
        val list = nodes.map { it.copy() }
        // Simple circular initial layout
        val centerX = 400f
        val centerY = 400f
        val radius = 150f
        list.forEachIndexed { index, node ->
            val angle = 2 * Math.PI * index / list.size
            node.x = centerX + radius * cos(angle).toFloat()
            node.y = centerY + radius * sin(angle).toFloat()
        }
        // Simple force simulation (5 iterations)
        repeat(5) {
            // Repulsion between nodes
            for (i in list.indices) {
                for (j in i + 1 until list.size) {
                    val dx = list[j].x - list[i].x
                    val dy = list[j].y - list[i].y
                    val dist = sqrt(dx * dx + dy * dy).coerceAtLeast(1f)
                    val force = 1000f / (dist * dist)
                    val fx = dx / dist * force
                    val fy = dy / dist * force
                    list[i].x -= fx; list[i].y -= fy
                    list[j].x += fx; list[j].y += fy
                }
            }
            // Attraction along edges
            edges.forEach { edge ->
                val source = list.find { it.id == edge.sourceId }
                val target = list.find { it.id == edge.targetId }
                if (source != null && target != null) {
                    val dx = target.x - source.x
                    val dy = target.y - source.y
                    val dist = sqrt(dx * dx + dy * dy).coerceAtLeast(1f)
                    val force = (dist - 120f) * 0.01f
                    val fx = dx / dist * force
                    val fy = dy / dist * force
                    source.x += fx; source.y += fy
                    target.x -= fx; target.y -= fy
                }
            }
        }
        list
    }

    val textColor = Color(0xFF1B2A4A)

    Canvas(
        modifier = modifier.fillMaxSize()
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, zoom, _ ->
                    scale = (scale * zoom).coerceIn(0.3f, 3f)
                    offsetX += pan.x
                    offsetY += pan.y
                }
            }
            .graphicsLayer {
                scaleX = scale; scaleY = scale
                translationX = offsetX; translationY = offsetY
            }
    ) {
        // Draw edges
        edges.forEach { edge ->
            val source = positionedNodes.find { it.id == edge.sourceId }
            val target = positionedNodes.find { it.id == edge.targetId }
            if (source != null && target != null) {
                drawLine(
                    color = Color(0xFFC0CADC),
                    start = Offset(source.x, source.y),
                    end = Offset(target.x, target.y),
                    strokeWidth = edge.weight * 2f
                )
            }
        }

        // Draw nodes
        positionedNodes.forEach { node ->
            val nodeRadius = 8f + node.importance * 16f
            val nodeColor = masteryColor(node.mastery)

            // Node circle
            drawCircle(nodeColor, nodeRadius, Offset(node.x, node.y))
            drawCircle(Color.White, nodeRadius - 3f, Offset(node.x, node.y))
            drawCircle(nodeColor, nodeRadius - 5f, Offset(node.x, node.y))

            // Label
            drawContext.canvas.nativeCanvas.drawText(
                node.label,
                node.x,
                node.y + nodeRadius + 16.dp.toPx(),
                android.graphics.Paint().apply {
                    color = textColor.hashCode()
                    textSize = 10.dp.toPx()
                    textAlign = android.graphics.Paint.Align.CENTER
                }
            )
        }
    }
}

private fun masteryColor(mastery: Float): Color {
    return when {
        mastery >= 0.8f -> Sage500
        mastery >= 0.6f -> Emerald500
        mastery >= 0.4f -> Amber500
        mastery >= 0.2f -> Navy500
        else -> Navy300
    }
}
