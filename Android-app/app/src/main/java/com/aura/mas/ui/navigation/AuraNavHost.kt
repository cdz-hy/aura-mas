package com.aura.mas.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.*
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.aura.mas.data.repository.AuthStore
import com.aura.mas.ui.auth.LoginScreen
import com.aura.mas.ui.auth.RegisterScreen
import com.aura.mas.ui.auth.AuthViewModel
import com.aura.mas.ui.plan.PlanCreateScreen
import com.aura.mas.ui.plan.PlanDetailScreen
import com.aura.mas.ui.note.NoteDetailScreen
import com.aura.mas.ui.quiz.QuizPlayerScreen
import com.aura.mas.ui.flashcard.FlashcardPlayerScreen
import com.aura.mas.ui.tree.KnowledgeTreeScreen
import com.aura.mas.ui.graph.KnowledgeGraphScreen
import com.aura.mas.ui.profile.SettingsScreen
import com.aura.mas.ui.profile.LearningProfileScreen
import com.aura.mas.ui.profile.PersonalInfoEditScreen
import com.aura.mas.ui.analytics.AnalyticsScreen
import com.aura.mas.ui.admin.EnhancedAdminUsersScreen
import com.aura.mas.ui.admin.EnhancedAdminLogsScreen
import com.aura.mas.ui.chat.StandaloneChatScreen
import com.aura.mas.ui.common.MainLayout
import com.aura.mas.ui.common.NotFoundScreen

@Composable
fun AuraNavHost() {
    val navController = rememberNavController()
    val authViewModel: AuthViewModel = hiltViewModel()
    val authStore = authViewModel.authStore

    var isSessionRestored by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        authStore.restoreSession()
        isSessionRestored = true
    }

    if (!isSessionRestored) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator()
        }
        return
    }

    val startDestination = remember {
        if (authStore.isLoggedIn.value) NavRoutes.MAIN else NavRoutes.LOGIN
    }

    NavHost(navController = navController, startDestination = startDestination) {
        composable(NavRoutes.LOGIN) {
            LoginScreen(
                onNavigateToRegister = { navController.navigate(NavRoutes.REGISTER) },
                onLoginSuccess = {
                    navController.navigate(NavRoutes.MAIN) {
                        popUpTo(NavRoutes.LOGIN) { inclusive = true }
                    }
                }
            )
        }
        composable(NavRoutes.REGISTER) {
            RegisterScreen(
                onNavigateToLogin = { navController.popBackStack() },
                onRegisterSuccess = {
                    navController.navigate(NavRoutes.LOGIN) {
                        popUpTo(NavRoutes.REGISTER) { inclusive = true }
                    }
                }
            )
        }
        composable(NavRoutes.PROFILE) {
            // Profile is handled in MainLayout inner nav
        }
        composable(NavRoutes.LEARNING_PROFILE) {
            LearningProfileScreen(
                onNavigateBack = { navController.popBackStack() }
            )
        }
        composable(NavRoutes.ANALYTICS) {
            AnalyticsScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(NavRoutes.MAIN) {
            MainLayout(navController = navController)
        }
        composable(NavRoutes.PLAN_CREATE) {
            PlanCreateScreen(onBack = { navController.popBackStack() })
        }
        composable(
            NavRoutes.PLAN_DETAIL,
            arguments = listOf(navArgument("planId") { type = NavType.LongType })
        ) {
            PlanDetailScreen(
                planId = it.arguments?.getLong("planId") ?: 0L,
                onBack = { navController.popBackStack() },
                onNavigateToQuiz = { resourceId -> navController.navigate(NavRoutes.quizPlayer(resourceId)) }
            )
        }
        composable(
            NavRoutes.NOTE_DETAIL,
            arguments = listOf(navArgument("noteId") { type = NavType.LongType })
        ) {
            NoteDetailScreen(
                noteId = it.arguments?.getLong("noteId") ?: 0L,
                onBack = { navController.popBackStack() },
                onNavigateToPlan = { planId -> navController.navigate(NavRoutes.planDetail(planId)) },
                onNavigateToFlashcards = { noteId -> navController.navigate(NavRoutes.flashcardPlayer(noteId)) }
            )
        }
        composable(
            NavRoutes.QUIZ_PLAYER,
            arguments = listOf(navArgument("resourceId") { type = NavType.LongType })
        ) {
            QuizPlayerScreen(
                resourceId = it.arguments?.getLong("resourceId") ?: 0L,
                onBack = { navController.popBackStack() }
            )
        }
        composable(
            NavRoutes.FLASHCARD_PLAYER,
            arguments = listOf(navArgument("noteId") { type = NavType.LongType })
        ) {
            FlashcardPlayerScreen(
                noteId = it.arguments?.getLong("noteId") ?: 0L,
                onBack = { navController.popBackStack() }
            )
        }
        composable(
            NavRoutes.KNOWLEDGE_TREE,
            arguments = listOf(navArgument("planId") { type = NavType.LongType })
        ) {
            KnowledgeTreeScreen(
                planId = it.arguments?.getLong("planId") ?: 0L,
                onBack = { navController.popBackStack() }
            )
        }
        composable(
            NavRoutes.KNOWLEDGE_GRAPH,
            arguments = listOf(navArgument("userId") { type = NavType.LongType })
        ) {
            KnowledgeGraphScreen(
                userId = it.arguments?.getLong("userId") ?: 0L,
                onBack = { navController.popBackStack() },
                onNavigateToNote = { noteId -> navController.navigate(NavRoutes.noteDetail(noteId)) },
                onNavigateToQuiz = { quizId -> navController.navigate(NavRoutes.quizPlayer(quizId)) }
            )
        }
        composable(NavRoutes.SETTINGS) {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onLogout = {
                    navController.navigate(NavRoutes.LOGIN) {
                        popUpTo(0) { inclusive = true }
                    }
                },
                onPersonalInfoClick = { navController.navigate(NavRoutes.PERSONAL_INFO_EDIT) },
                onCacheClick = { navController.navigate(NavRoutes.CACHE_MANAGEMENT) }
            )
        }
        composable(NavRoutes.CACHE_MANAGEMENT) {
            com.aura.mas.ui.profile.CacheManagementScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(NavRoutes.PERSONAL_INFO_EDIT) {
            PersonalInfoEditScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(NavRoutes.ADMIN_DASHBOARD) {
            com.aura.mas.ui.admin.AdminDashboardScreen(
                onUsersClick = { navController.navigate(NavRoutes.ADMIN_USERS) },
                onLogsClick = { navController.navigate(NavRoutes.ADMIN_LOGS) },
                onBack = { navController.popBackStack() }
            )
        }
        composable(NavRoutes.ADMIN_USERS) {
            EnhancedAdminUsersScreen(onBack = { navController.popBackStack() })
        }
        composable(NavRoutes.ADMIN_LOGS) {
            EnhancedAdminLogsScreen(onBack = { navController.popBackStack() })
        }
        composable(NavRoutes.CHAT) {
            StandaloneChatScreen(onBack = { navController.popBackStack() })
        }
        composable(NavRoutes.NOT_FOUND) {
            NotFoundScreen(onBack = { navController.popBackStack() })
        }
    }
}
