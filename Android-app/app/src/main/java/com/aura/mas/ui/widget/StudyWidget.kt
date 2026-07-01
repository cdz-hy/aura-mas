package com.aura.mas.ui.widget

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.*
import androidx.glance.unit.ColorProvider
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.*
import androidx.glance.layout.*
import androidx.glance.text.*
import com.aura.mas.MainActivity

class StudyWidget : GlanceAppWidget() {
    override suspend fun provideGlance(context: Context, id: GlanceId) {
        provideContent {
            StudyWidgetContent()
        }
    }
}

@Composable
private fun StudyWidgetContent() {
    val bgColor = androidx.glance.color.ColorProvider(day = Color(0xFFFFFFFF), night = Color(0xFF1B2A4A))
    val primaryColor = androidx.glance.color.ColorProvider(day = Color(0xFF2E4376), night = Color(0xFF98A8C8))
    val secondaryColor = androidx.glance.color.ColorProvider(day = Color(0xFF6B7FAE), night = Color(0xFF6B7FAE))
    val surfaceColor = androidx.glance.color.ColorProvider(day = Color(0xFFF0F3F9), night = Color(0xFF1E293B))
    val textColor = androidx.glance.color.ColorProvider(day = Color(0xFF0D1424), night = Color(0xFFE2E8F0))

    Column(
        modifier = GlanceModifier.fillMaxSize().padding(16.dp)
            .background(bgColor)
            .clickable(actionStartActivity<MainActivity>())
    ) {
        Text(
            "AURA MAS",
            style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold, color = primaryColor)
        )
        Spacer(GlanceModifier.height(8.dp))

        Row(GlanceModifier.fillMaxWidth()) {
            StatBox("学习计划", "12", GlanceModifier.defaultWeight(), surfaceColor, secondaryColor, textColor)
            Spacer(GlanceModifier.width(8.dp))
            StatBox("学习时长", "48h", GlanceModifier.defaultWeight(), surfaceColor, secondaryColor, textColor)
        }

        Spacer(GlanceModifier.height(8.dp))

        Row(GlanceModifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text("待复习闪卡", style = TextStyle(fontSize = 12.sp, color = secondaryColor))
            Spacer(GlanceModifier.defaultWeight())
            Text("5 张", style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Medium, color = primaryColor))
        }
    }
}

@Composable
private fun StatBox(
    label: String,
    value: String,
    modifier: GlanceModifier = GlanceModifier,
    bgColor: ColorProvider,
    labelColor: ColorProvider,
    valueColor: ColorProvider
) {
    Column(
        modifier = modifier.padding(12.dp).background(bgColor).cornerRadius(12.dp)
    ) {
        Text(label, style = TextStyle(fontSize = 10.sp, color = labelColor))
        Spacer(GlanceModifier.height(4.dp))
        Text(value, style = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.Bold, color = valueColor))
    }
}

class StudyWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget = StudyWidget()
}
