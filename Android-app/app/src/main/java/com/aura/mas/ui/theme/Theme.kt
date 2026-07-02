package com.aura.mas.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking

private val LightColorScheme = lightColorScheme(
    primary = Navy800,
    onPrimary = Color.White,
    primaryContainer = Navy100,
    onPrimaryContainer = Navy900,
    secondary = Sage700,
    onSecondary = Color.White,
    secondaryContainer = Sage100,
    onSecondaryContainer = Sage900,
    tertiary = Cream500,
    onTertiary = Navy900,
    tertiaryContainer = Cream200,
    onTertiaryContainer = Cream900,
    background = Cream50,
    onBackground = Navy900,
    surface = Color.White,
    onSurface = Navy900,
    surfaceVariant = Navy50,
    onSurfaceVariant = Navy500,
    outline = Navy200,
    outlineVariant = Navy100,
    error = Red500,
    onError = Color.White,
    errorContainer = Red50,
    onErrorContainer = Red500,
    surfaceContainerLowest = Color.White,
    surfaceContainerLow = Cream50,
    surfaceContainer = Cream100,
    surfaceContainerHigh = Cream200,
    surfaceContainerHighest = Navy50,
    inverseSurface = Navy900,
    inverseOnSurface = Navy50,
    inversePrimary = Navy200,
)

private val DarkColorScheme = darkColorScheme(
    primary = Navy200,
    onPrimary = Navy900,
    primaryContainer = NavyDark700,
    onPrimaryContainer = Navy100,
    secondary = Sage200,
    onSecondary = Sage900,
    secondaryContainer = Sage700,
    onSecondaryContainer = Sage100,
    tertiary = Cream500,
    onTertiary = Cream900,
    tertiaryContainer = CreamDark,
    onTertiaryContainer = Cream100,
    background = NavyDark900,
    onBackground = Cream50,
    surface = NavyDark800,
    onSurface = Cream50,
    surfaceVariant = NavyDark700,
    onSurfaceVariant = Navy200,
    outline = NavyDark800,
    outlineVariant = NavyDark900,
    error = Red500,
    onError = Color.White,
    errorContainer = Red500,
    onErrorContainer = Color.White,
    surfaceContainerLowest = NavyDark900,
    surfaceContainerLow = NavyDark800,
    surfaceContainer = NavyDark700,
    surfaceContainerHigh = NavyDark800,
    surfaceContainerHighest = NavyDark700,
    inverseSurface = Cream50,
    inverseOnSurface = NavyDark900,
    inversePrimary = Navy800,
)

private val OceanLightScheme = lightColorScheme(
    primary = Color(0xFF0077B6),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFCAF0F8),
    secondary = Color(0xFF00B4D8),
    background = Color(0xFFF0F8FF),
    surface = Color.White,
    onBackground = Color(0xFF03045E),
    onSurface = Color(0xFF03045E),
)

private val ForestLightScheme = lightColorScheme(
    primary = Color(0xFF2D6A4F),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD8F3DC),
    secondary = Color(0xFF40916C),
    background = Color(0xFFF5FFF5),
    surface = Color.White,
    onBackground = Color(0xFF1B4332),
    onSurface = Color(0xFF1B4332),
)

private val SunsetLightScheme = lightColorScheme(
    primary = Color(0xFFE85D04),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFFF3E0),
    secondary = Color(0xFFF48C06),
    background = Color(0xFFFFFBF5),
    surface = Color.White,
    onBackground = Color(0xFF370617),
    onSurface = Color(0xFF370617),
)

@Composable
fun AuraTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    var themeString by remember {
        mutableStateOf(
            context.getSharedPreferences("aura_prefs", android.content.Context.MODE_PRIVATE)
                .getString("app_theme", null)
        )
    }

    DisposableEffect(context) {
        val prefs = context.getSharedPreferences("aura_prefs", android.content.Context.MODE_PRIVATE)
        val listener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { sharedPreferences, key ->
            if (key == "app_theme") {
                themeString = sharedPreferences.getString("app_theme", null)
            }
        }
        prefs.registerOnSharedPreferenceChangeListener(listener)
        onDispose {
            prefs.unregisterOnSharedPreferenceChangeListener(listener)
        }
    }

    val savedTheme = try {
        themeString?.let { AppTheme.valueOf(it) }
    } catch (_: Exception) { null }

    val colorScheme = when (savedTheme) {
        AppTheme.DARK -> DarkColorScheme
        AppTheme.OCEAN -> OceanLightScheme
        AppTheme.FOREST -> ForestLightScheme
        AppTheme.SUNSET -> SunsetLightScheme
        else -> if (darkTheme) DarkColorScheme else LightColorScheme
    }

    val isDark = savedTheme == AppTheme.DARK || (savedTheme == null && darkTheme)

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Color.Transparent.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !isDark
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
