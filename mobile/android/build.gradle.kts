// Repositorios compartidos por los plugins y dependencias de los módulos Android.
allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

// Mantiene los artefactos de Gradle en el directorio build común de la app móvil.
val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

// Evalúa primero :app para que sus configuraciones estén disponibles en los subproyectos.
subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// Tarea estándar para limpiar artefactos locales de compilación.
tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
