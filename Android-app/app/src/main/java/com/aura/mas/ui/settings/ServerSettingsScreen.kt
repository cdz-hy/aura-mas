package com.aura.mas.ui.settings

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aura.mas.data.repository.ServerConfig
import com.aura.mas.util.Constants

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ServerSettingsScreen(
    serverConfig: ServerConfig,
    onBack: () -> Unit
) {
    val currentJavaUrl by serverConfig.javaUrl.collectAsState()
    val currentPythonUrl by serverConfig.pythonUrl.collectAsState()

    var javaUrl by remember(currentJavaUrl) { mutableStateOf(currentJavaUrl.trimEnd('/')) }
    var pythonUrl by remember(currentPythonUrl) { mutableStateOf(currentPythonUrl.trimEnd('/')) }
    var saved by remember { mutableStateOf(false) }
    val scope = androidx.compose.runtime.rememberCoroutineScope()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("服务器设置") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "返回")
                    }
                },
                actions = {
                    IconButton(onClick = {
                        javaUrl = Constants.JAVA_BASE_URL.trimEnd('/')
                        pythonUrl = Constants.PYTHON_BASE_URL.trimEnd('/')
                    }) {
                        Icon(Icons.Default.Refresh, "恢复默认")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Info card
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
            ) {
                Text(
                    text = "修改服务器地址后需要重新启动应用才能生效。默认地址适用于模拟器（10.0.2.2）或局域网服务器。",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                    modifier = Modifier.padding(12.dp)
                )
            }

            // Java Backend URL
            Text(
                "Java 后端地址",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold
            )
            OutlinedTextField(
                value = javaUrl,
                onValueChange = { javaUrl = it; saved = false },
                label = { Text("Java Backend URL") },
                placeholder = { Text("http://10.112.101.250:8080/") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            // Python Backend URL
            Text(
                "Python 后端地址",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold
            )
            OutlinedTextField(
                value = pythonUrl,
                onValueChange = { pythonUrl = it; saved = false },
                label = { Text("Python Backend URL") },
                placeholder = { Text("http://10.112.101.250:8002/") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            Spacer(Modifier.height(8.dp))

            // Save button
            Button(
                onClick = {
                    scope.launch {
                        serverConfig.save(javaUrl, pythonUrl)
                        saved = true
                    }
                },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp),
                enabled = javaUrl.isNotBlank() && pythonUrl.isNotBlank()
            ) {
                Text(if (saved) "已保存，重启应用生效" else "保存")
            }

            // Reset button
            OutlinedButton(
                onClick = {
                    scope.launch {
                        serverConfig.resetToDefaults()
                        saved = true
                    }
                },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("恢复默认地址")
            }

            // Current values
            Spacer(Modifier.height(16.dp))
            Text(
                "当前生效地址：",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
            )
            Text(
                "Java: $currentJavaUrl",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
            )
            Text(
                "Python: $currentPythonUrl",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
            )
        }
    }
}
