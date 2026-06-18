// AI Voice Cover - Tauri Backend
// Manages the Python sidecar process and provides native APIs

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

const BACKEND_PORT: u16 = 9527;

struct AppState {
    sidecar: Mutex<Option<Child>>,
}

#[tauri::command]
fn get_backend_port() -> u16 {
    BACKEND_PORT
}

#[tauri::command]
fn get_backend_url() -> String {
    format!("http://127.0.0.1:{}", BACKEND_PORT)
}

#[tauri::command]
async fn check_backend() -> Result<String, String> {
    let url = format!("http://127.0.0.1:{}/api/v1/health", BACKEND_PORT);
    match reqwest::get(&url).await {
        Ok(resp) => resp.text().await.map_err(|e| e.to_string()),
        Err(e) => Err(format!("Backend not ready: {}", e)),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            sidecar: Mutex::new(None),
        })
        .setup(move |app| {
            let resource_dir = app.path().resource_dir().unwrap();
            let sidecar_dir = resource_dir.join("sidecar");
            let launcher = sidecar_dir.join("sidecar-launcher.py");

            println!("Resource dir: {:?}", resource_dir);
            println!("Sidecar dir: {:?}", sidecar_dir);
            println!("Launcher exists: {}", launcher.exists());

            // Debug: list sidecar contents
            if let Ok(entries) = std::fs::read_dir(&sidecar_dir) {
                for entry in entries.flatten() {
                    println!("  {:?}", entry.path());
                }
            }

            // Debug: check embedded python
            let py_dir = sidecar_dir.join("python");
            println!("Python dir: {:?}", py_dir);
            println!("Python dir exists: {}", py_dir.exists());
            if let Ok(entries) = std::fs::read_dir(&py_dir) {
                for entry in entries.flatten() {
                    println!("  {:?}", entry.path());
                }
            }

            if !launcher.exists() {
                eprintln!("Launcher not found at {:?}", launcher);
                eprintln!("Resource dir: {:?}", resource_dir);
                return Ok(());
            }

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
                .env("AVC_PORT", BACKEND_PORT.to_string())
                .spawn()
                .expect("Failed to start backend");

            *app.state::<AppState>().sidecar.lock().unwrap() = Some(child);

            // Wait for backend to be ready (up to 60s — first run installs deps)
            std::thread::spawn(move || {
                for _ in 0..60 {
                    std::thread::sleep(std::time::Duration::from_secs(1));
                    if std::net::TcpStream::connect(("127.0.0.1", BACKEND_PORT)).is_ok() {
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
        eprintln!("[find_python] Checking embedded: {:?} exists={}", embedded, embedded.exists());
        if embedded.exists() {
            return Some(embedded);
        }
    }

    // 2. System Python on PATH
    for name in &["python3", "python"] {
        if let Ok(output) = Command::new(name).arg("--version").output() {
            if output.status.success() {
                let ver = String::from_utf8_lossy(&output.stdout).to_string()
                    + &String::from_utf8_lossy(&output.stderr);
                eprintln!("[find_python] {} version: {:?}", name, ver.trim());
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

    eprintln!("[find_python] No suitable Python found");
    None
}
