// AI Voice Cover - Tauri Backend
// Manages the Python sidecar process and provides native APIs

use std::process::{Command, Child};
use std::sync::Mutex;
use std::net::TcpListener;
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
        Ok(resp) => resp.text().map_err(|e| e.to_string()),
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
            // Start Python sidecar
            let sidecar_name = if cfg!(target_os = "windows") {
                "ai-voice-cover-server-x86_64-pc-windows-msvc.exe"
            } else if cfg!(target_os = "macos") {
                "ai-voice-cover-server-apple-darwin"
            } else {
                "ai-voice-cover-server-x86_64-unknown-linux-gnu"
            };

            let sidecar_path = app.path()
                .resource_dir()
                .unwrap()
                .join("sidecar")
                .join(sidecar_name);

            if sidecar_path.exists() {
                let child = Command::new(&sidecar_path)
                    .env("AVC_PORT", port.to_string())
                    .spawn()
                    .expect("Failed to start backend");

                *app.state::<AppState>().sidecar.lock().unwrap() = Some(child);

                // Wait for backend to be ready
                std::thread::spawn(move || {
                    for _ in 0..30 {
                        std::thread::sleep(std::time::Duration::from_secs(1));
                        if let Ok(listener) = TcpListener::connect(("127.0.0.1", port)) {
                            drop(listener);
                            break;
                        }
                    }
                });
            } else {
                // Dev mode - assume backend is running externally
                println!("Sidecar not found at {:?}, using external backend", sidecar_path);
            }

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
