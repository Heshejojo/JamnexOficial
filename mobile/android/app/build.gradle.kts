plugins {
    id("com.android.application")
    // El plugin Flutter va después de los plugins Android y Kotlin para leer su configuración.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    // Namespace Kotlin/Android y versiones de SDK proporcionadas por Flutter.
    namespace = "com.example.agente_cfe"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // Identificador único de la aplicación en Android y en los canales Flutter.
        applicationId = "com.example.agente_cfe"
        // Flutter suministra los SDK mínimos y destino según la configuración del proyecto.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Gradle toma la versión de pubspec.yaml para mantener una sola fuente de verdad.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // Firma temporal de depuración: debe sustituirse por una clave de publicación.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

dependencies {
    // WorkManager ejecuta sincronizaciones periódicas y al recuperar conectividad.
    implementation("androidx.work:work-runtime-ktx:2.9.1")
}
