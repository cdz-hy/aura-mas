package com.aura.mas.ui.theme

import androidx.compose.ui.graphics.Color
import com.aura.mas.util.Constants
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

enum class AppTheme(val label: String) {
    LIGHT("浅色"),
    DARK("深色"),
    OCEAN("海洋"),
    FOREST("森林"),
    SUNSET("日落");

    companion object {
        val THEME_KEY = stringPreferencesKey("app_theme")
    }
}

data class ThemeColors(
    val primary: Color,
    val primaryContainer: Color,
    val secondary: Color,
    val background: Color,
    val surface: Color,
    val onPrimary: Color,
    val onBackground: Color,
    val onSurface: Color
)

val OceanColors = ThemeColors(
    primary = Color(0xFF0077B6),
    primaryContainer = Color(0xFFCAF0F8),
    secondary = Color(0xFF00B4D8),
    background = Color(0xFFF0F8FF),
    surface = Color.White,
    onPrimary = Color.White,
    onBackground = Color(0xFF03045E),
    onSurface = Color(0xFF03045E)
)

val ForestColors = ThemeColors(
    primary = Color(0xFF2D6A4F),
    primaryContainer = Color(0xFFD8F3DC),
    secondary = Color(0xFF40916C),
    background = Color(0xFFF5FFF5),
    surface = Color.White,
    onPrimary = Color.White,
    onBackground = Color(0xFF1B4332),
    onSurface = Color(0xFF1B4332)
)

val SunsetColors = ThemeColors(
    primary = Color(0xFFE85D04),
    primaryContainer = Color(0xFFFFF3E0),
    secondary = Color(0xFFF48C06),
    background = Color(0xFFFFFBF5),
    surface = Color.White,
    onPrimary = Color.White,
    onBackground = Color(0xFF370617),
    onSurface = Color(0xFF370617)
)

@Singleton
class ThemeManager @Inject constructor(
    private val dataStore: DataStore<Preferences>
) {
    val themeFlow: Flow<AppTheme> = dataStore.data.map { prefs ->
        val name = prefs[AppTheme.THEME_KEY] ?: AppTheme.LIGHT.name
        try { AppTheme.valueOf(name) } catch (e: Exception) { AppTheme.LIGHT }
    }

    suspend fun setTheme(theme: AppTheme) {
        dataStore.edit { prefs ->
            prefs[AppTheme.THEME_KEY] = theme.name
        }
    }
}
