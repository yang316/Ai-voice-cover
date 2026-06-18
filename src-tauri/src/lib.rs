// AI Voice Cover - Tauri Backend
// Manages the Python sidecar process and provides native APIs

use std::net::TcpListener;
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

struct AppState {
    sidecar: Mutex<Option<Child>>,
    port: Mutex<u16>,
}

fn find_free_port() -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    listener.local_addr().unwrap().port()
}

#[tauri::command]
fn get_backend_port(state: tauri::State<AppState>) -> u16 {
    *state.port.lock().unwrap()
}

#[tauri::command]
fn get_backend_url(state: tauri::State<AppState>) -> String {
    let port = *state.port.lock().unwrap();
    format!("http://127.0.0.1:{}", port)
}

#[tauri::command]
async fn check_backend(state: tauri::State<'_, AppState>) -> Result<String, String> {
    let port = *state.port.lock().unwrap();
    let url = format!("http://127.0.0.1:{}/api/v1/health", port);

    match reqwest::get(&url).await {
        Ok(resp) => resp.text().await.map_err(|e| e.to_string()),
        Err(e) => Err(format!("Backend not ready: {}", e)),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let port = find_free_port();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            sidecar: Mutex::new(None),
            port: Mutex::new(port),
        })
        .setup(move |app| {
            let resource_dir = app.path().resource_dir().unwrap();
            let sidecar_dir = resource_dir.join("sidecar");
            let launcher = sidecar_dir.join("sidecar-launcher.py");

            if !launcher.exists() {
                eprintln!("Launcher not found at {:?}", launcher);
                eprintln!("Resource dir: {:?}", resource_dir);
                return Ok(());
            }

            // Find Python — embedded in bundle (Windows) or system
            let python = find_python(&sidecar_dir);

            let python = match python {
                Some(p) => p,
                None => {
                    eprintln!("Python 3.11+ not found. Please install Python.");
                    return Ok(());
                }
            };

            println!("Python: {:?}", python);
            println!("Launcher: {:?}", launcher);

            let child = Command::new(&python)
                .arg(&launcher)
                .current_dir(&sidecar_dir)
                .env("AVC_PORT", port.to_string())
                .spawn()
                .expect("Failed to start backend");

            *app.state::<AppState>().sidecar.lock().unwrap() = Some(child);

            // Wait for backend to be ready (up to 60s — first run installs deps)
            std::thread::spawn(move || {
                for _ in 0..60 {
                    std::thread::sleep(std::time::Duration::from_secs(1));
                    if std::net::TcpStream::connect(("127.0.0.1", port)).is_ok() {
                        break;
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_port,
            get_backend_url,
            check_backend,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn find_python(sidecar_dir: &std::path::Path) -> Option<std::path::PathBuf> {
    // 1. Embedded Python in bundle (Windows)
    #[cfg(target_os = "windows")]
    {
        let embedded = sidecar_dir.join("python").join("python.exe");
        if embedded.exists() {
            return Some(embedded);
        }
    }

    // 2. System Python on PATH
    for name in &["python3", "python"] {
        if let Ok(output) = Command::new(name).arg("--version").output() {
            if output.status.success() {
                if let Ok(ver) = String::from_utf8(output.stdout) {
                    if ver.contains("3.11") || ver.contains("3.12") || ver.contains("3.13") {
                        #[cfg(target_os = "windows")]
                        let cmd = "where";
                        #[cfg(not(target_os = "windows"))]
                        let cmd = "which";

                        if let Ok(path_out) = Command::new(cmd).arg(name).output() {
                            if let Ok(path_str) = String::from_utf8(path_out.stdout) {
                                let path = path_str.trim().lines().next().unwrap_or("");
                                if !path.is_empty() {
                                    return Some(std::path::PathBuf::from(path));
                                }
                            }
                        }
                        return Some(std::path::PathBuf::from(name));
                    }
                }
            }
        }
    }

    None
}
