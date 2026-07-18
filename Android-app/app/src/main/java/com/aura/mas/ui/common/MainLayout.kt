package com.aura.mas.ui.common

import androidx.compose.animation.*
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.aura.mas.ui.navigation.NavRoutes
import com.aura.mas.ui.dashboard.DashboardScreen
import com.aura.mas.ui.plan.PlanListScreen
import com.aura.mas.ui.note.NoteListScreen
import com.aura.mas.ui.analytics.AnalyticsScreen
import com.aura.mas.ui.profile.ProfileScreen
import com.aura.mas.ui.common.StrategyNotification
import com.aura.mas.ui.common.StrategyViewModel
import androidx.hilt.navigation.compose.hiltViewModel

data class BottomNavItem(
    val route: String,
    val label: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector
)

val bottomNavItems = listOf(
    BottomNavItem(NavRoutes.DASHBOARD, "首页", Icons.Filled.Home, Icons.Outlined.Home),
    BottomNavItem(NavRoutes.PLAN_LIST, "学习计划", Icons.Filled.MenuBook, Icons.Outlined.MenuBook),
    BottomNavItem(NavRoutes.NOTE_LIST, "笔记", Icons.Filled.Description, Icons.Outlined.Description),
    BottomNavItem(NavRoutes.PROFILE, "我的", Icons.Filled.Person, Icons.Outlined.Person)
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainLayout(navController: NavController) {
    val innerNavController = rememberNavController()
    val navBackStackEntry by innerNavController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route
    val strategyViewModel: StrategyViewModel = hiltViewModel()

    val pendingCount by strategyViewModel.pendingCount.collectAsState()
    val strategies by strategyViewModel.strategies.collectAsState()
    val strategyLoading by strategyViewModel.loading.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AURA 智学", fontWeight = FontWeight.SemiBold) },
                actions = {
                    StrategyNotification(
                        pendingCount = pendingCount,
                        strategies = strategies,
                        loading = strategyLoading,
                        onLoadStrategies = { strategyViewModel.loadStrategies() },
                        onAccept = { strategyViewModel.acceptStrategy(it) },
                        onReject = { strategyViewModel.rejectStrategy(it) }
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                tonalElevation = 0.dp
            ) {
                bottomNavItems.forEach { item ->
                    val selected = currentRoute == item.route
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            if (currentRoute != item.route) {
                                innerNavController.navigate(item.route) {
                                    popUpTo(NavRoutes.DASHBOARD) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            }
                        },
                        icon = {
                            Icon(
                                if (selected) item.selectedIcon else item.unselectedIcon,
                                contentDescription = item.label
                            )
                        },
                        label = { Text(item.label, style = MaterialTheme.typography.labelSmall) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                            unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = innerNavController,
            startDestination = NavRoutes.DASHBOARD,
            modifier = Modifier.padding(padding)
        ) {
            composable(NavRoutes.DASHBOARD) {
                DashboardScreen(
                    onPlanClick = { navController.navigate(NavRoutes.planDetail(it)) },
                    onViewAllPlans = {
                        innerNavController.navigate(NavRoutes.PLAN_LIST) {
                            popUpTo(NavRoutes.DASHBOARD) { saveState = true }
                            launchSingleTop = true
                        }
                    }
                )
            }
            composable(NavRoutes.PLAN_LIST) {
                PlanListScreen(
                    onPlanClick = { navController.navigate(NavRoutes.planDetail(it)) },
                    onCreatePlan = { navController.navigate(NavRoutes.PLAN_CREATE) }
                )
            }
            composable(NavRoutes.NOTE_LIST) {
                NoteListScreen(
                    onNoteClick = { navController.navigate(NavRoutes.noteDetail(it)) }
                )
            }
            composable(NavRoutes.PROFILE) {
                ProfileScreen(
                    onLearningProfileClick = { navController.navigate(NavRoutes.LEARNING_PROFILE) },
                    onSettingsClick = { navController.navigate(NavRoutes.SETTINGS) },
                    onAnalyticsClick = { navController.navigate(NavRoutes.ANALYTICS) },
                    onKnowledgeGraphClick = { userId -> navController.navigate(NavRoutes.knowledgeGraph(userId)) }
                )
            }
        }
    }
}
