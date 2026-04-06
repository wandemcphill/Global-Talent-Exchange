#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Gtex.Match3D.Editor
{
    public static class GtexAndroidBuildTools
    {
        private const string ApkFileName = "GTEXMatchEngine.apk";

        [MenuItem("Tools/GTEX/Android/Configure SDK From Environment")]
        public static void ConfigureSdkFromEnvironmentMenu()
        {
            ConfigureSdkFromEnvironment();
            Debug.Log("GTEX Android SDK path: " + AndroidExternalToolsSettings.sdkRootPath);
        }

        [MenuItem("Tools/GTEX/Android/Validate External Tools")]
        public static void ValidateExternalToolsMenu()
        {
            EnsureExternalToolsConfigured();
            Debug.Log("GTEX Android External Tools are configured.");
        }

        [MenuItem("Tools/GTEX/Android/Build APK")]
        public static void BuildApkMenu()
        {
            EnsureExternalToolsConfigured();
            string outputPath = EditorUtility.SaveFilePanel(
                "Build GTEX Match Engine APK",
                Path.GetDirectoryName(ResolveDefaultApkPath()),
                Path.GetFileNameWithoutExtension(ApkFileName),
                "apk");
            if (string.IsNullOrWhiteSpace(outputPath))
            {
                return;
            }

            BuildAndroidPlayer(outputPath, exportProject: false);
        }

        [MenuItem("Tools/GTEX/Android/Export Unity Library")]
        public static void ExportUnityLibraryMenu()
        {
            EnsureExternalToolsConfigured();
            string outputPath = EditorUtility.OpenFolderPanel(
                "Export GTEX Unity Android Library",
                ResolveDefaultUnityExportDirectory(),
                string.Empty);
            if (string.IsNullOrWhiteSpace(outputPath))
            {
                return;
            }

            BuildAndroidPlayer(outputPath, exportProject: true);
        }

        public static void BuildApkFromCommandLine()
        {
            EnsureExternalToolsConfigured();
            BuildAndroidPlayer(ResolveDefaultApkPath(), exportProject: false);
        }

        public static void ExportUnityLibraryFromCommandLine()
        {
            EnsureExternalToolsConfigured();
            BuildAndroidPlayer(ResolveDefaultUnityExportDirectory(), exportProject: true);
        }

        private static void EnsureExternalToolsConfigured()
        {
            ConfigureSdkFromEnvironment();

            string sdkPath = AndroidExternalToolsSettings.sdkRootPath;
            if (string.IsNullOrWhiteSpace(sdkPath) || !Directory.Exists(sdkPath))
            {
                throw new BuildFailedException(
                    "Unity External Tools SDK path is not configured. Set Edit > Preferences > External Tools > Android SDK to a valid Android SDK folder.");
            }
        }

        private static void ConfigureSdkFromEnvironment()
        {
            if (Directory.Exists(AndroidExternalToolsSettings.sdkRootPath))
            {
                return;
            }

            string sdkPath = Environment.GetEnvironmentVariable("ANDROID_SDK_ROOT");
            if (string.IsNullOrWhiteSpace(sdkPath))
            {
                sdkPath = Environment.GetEnvironmentVariable("ANDROID_HOME");
            }

            if (!string.IsNullOrWhiteSpace(sdkPath) && Directory.Exists(sdkPath))
            {
                AndroidExternalToolsSettings.sdkRootPath = sdkPath;
            }
        }

        private static void BuildAndroidPlayer(string outputPath, bool exportProject)
        {
            string[] scenes = ResolveBuildScenes();
            if (scenes.Length == 0)
            {
                throw new BuildFailedException(
                    "No saved Unity scenes are enabled for Android. Save a scene with MatchSceneBootstrap and add it to Build Settings.");
            }

            if (exportProject)
            {
                Directory.CreateDirectory(outputPath);
            }
            else
            {
                Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? outputPath);
            }
            EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android);

            bool previousExportProject = EditorUserBuildSettings.exportAsGoogleAndroidProject;
            AndroidBuildSystem previousBuildSystem = EditorUserBuildSettings.androidBuildSystem;

            try
            {
                EditorUserBuildSettings.androidBuildSystem = AndroidBuildSystem.Gradle;
                EditorUserBuildSettings.exportAsGoogleAndroidProject = exportProject;

                BuildPlayerOptions options = new BuildPlayerOptions
                {
                    scenes = scenes,
                    target = BuildTarget.Android,
                    locationPathName = outputPath,
                    options = BuildOptions.None,
                };

                BuildReport report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new BuildFailedException(
                        "Android build failed with result: " + report.summary.result);
                }

                Debug.Log((exportProject ? "Unity library export" : "APK build") + " complete: " + outputPath);
            }
            finally
            {
                EditorUserBuildSettings.exportAsGoogleAndroidProject = previousExportProject;
                EditorUserBuildSettings.androidBuildSystem = previousBuildSystem;
            }
        }

        private static string[] ResolveBuildScenes()
        {
            string[] enabledScenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled && !string.IsNullOrWhiteSpace(scene.path))
                .Select(scene => scene.path)
                .ToArray();
            if (enabledScenes.Length > 0)
            {
                return enabledScenes;
            }

            string activeScenePath = EditorSceneManager.GetActiveScene().path;
            if (!string.IsNullOrWhiteSpace(activeScenePath))
            {
                return new[] { activeScenePath };
            }

            return Array.Empty<string>();
        }

        private static string ResolveDefaultApkPath()
        {
            return Path.Combine(ResolveDefaultBuildDirectory(), ApkFileName);
        }

        private static string ResolveDefaultUnityExportDirectory()
        {
            string unityProjectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string gtexAndroidRoot = Path.GetFullPath(Path.Combine(unityProjectRoot, "..", "frontend", "android"));
            if (Directory.Exists(gtexAndroidRoot))
            {
                return Path.Combine(gtexAndroidRoot, "unityExport");
            }

            return Path.Combine(ResolveDefaultBuildDirectory(), "unityExport");
        }

        private static string ResolveDefaultBuildDirectory()
        {
            string unityProjectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string buildDirectory = Path.Combine(unityProjectRoot, "Builds", "Android");
            Directory.CreateDirectory(buildDirectory);
            return buildDirectory;
        }
    }
}
#endif
