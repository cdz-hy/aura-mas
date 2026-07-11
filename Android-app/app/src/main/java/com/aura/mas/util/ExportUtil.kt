package com.aura.mas.util

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.net.Uri
import androidx.core.content.FileProvider
import com.aura.mas.data.model.Note
import java.io.File
import java.io.FileOutputStream

object ExportUtil {

    fun exportNoteToPdf(context: Context, note: Note): Uri {
        val document = PdfDocument()
        val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create()
        var page = document.startPage(pageInfo)
        var canvas: Canvas = page.canvas

        val titlePaint = Paint().apply {
            textSize = 24f
            isFakeBoldText = true
            color = android.graphics.Color.parseColor("#0D1424")
        }
        val bodyPaint = Paint().apply {
            textSize = 14f
            color = android.graphics.Color.parseColor("#1B2A4A")
        }
        val metaPaint = Paint().apply {
            textSize = 10f
            color = android.graphics.Color.parseColor("#6B7FAE")
        }

        var y = 60f
        val marginLeft = 50f
        val maxWidth = 495f

        // Title
        canvas.drawText(note.noteName, marginLeft, y, titlePaint)
        y += 30f

        // Date
        note.updatedAt?.let {
            canvas.drawText("更新时间: $it", marginLeft, y, metaPaint)
            y += 25f
        }

        // Divider
        canvas.drawLine(marginLeft, y, marginLeft + maxWidth, y, metaPaint)
        y += 20f

        // Content - split by lines and handle page breaks
        val lines = note.content.split("\n")
        for (line in lines) {
            if (y > 800f) {
                document.finishPage(page)
                val newPageInfo = PdfDocument.PageInfo.Builder(595, 842, document.pages.size + 1).create()
                page = document.startPage(newPageInfo)
                canvas = page.canvas
                y = 60f
            }

            // Word wrap
            val words = line.split(" ")
            var currentLine = ""
            for (word in words) {
                val testLine = if (currentLine.isEmpty()) word else "$currentLine $word"
                if (bodyPaint.measureText(testLine) > maxWidth) {
                    canvas.drawText(currentLine, marginLeft, y, bodyPaint)
                    y += 20f
                    currentLine = word
                    if (y > 800f) {
                        document.finishPage(page)
                        val newPageInfo = PdfDocument.PageInfo.Builder(595, 842, document.pages.size + 1).create()
                        page = document.startPage(newPageInfo)
                        canvas = page.canvas
                        y = 60f
                    }
                } else {
                    currentLine = testLine
                }
            }
            if (currentLine.isNotEmpty()) {
                canvas.drawText(currentLine, marginLeft, y, bodyPaint)
                y += 20f
            }
        }

        document.finishPage(page)

        val file = File(context.cacheDir, "note_${note.id}.pdf")
        FileOutputStream(file).use { out ->
            document.writeTo(out)
        }
        document.close()

        return FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
    }

    fun shareExportedFile(context: Context, uri: Uri, title: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "application/pdf"
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_SUBJECT, title)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, "分享笔记"))
    }
}
