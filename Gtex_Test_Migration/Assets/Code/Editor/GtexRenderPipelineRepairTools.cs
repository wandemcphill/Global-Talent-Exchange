using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace FStudio.GTEX.Editor
{
    public static class GtexRenderPipelineRepairTools
    {
        private const string PcRpAssetPath = "Assets/Settings/PC_RPAsset.asset";
        private const string MobileRpAssetPath = "Assets/Settings/Mobile_RPAsset.asset";
        private const string PcRendererAssetPath = "Assets/Settings/PC_Renderer.asset";
        private const string MobileRendererAssetPath = "Assets/Settings/Mobile_Renderer.asset";
        private const string UrpGlobalSettingsAssetPath = "Assets/Settings/UniversalRenderPipelineGlobalSettings.asset";

        [MenuItem("GTEX/Repair Standalone Render Pipeline Assets")]
        public static void RepairStandaloneRenderPipelineAssets()
        {
            RepairStandaloneRenderPipelineAssetsInternal();
        }

        public static void RepairStandaloneRenderPipelineAssetsFromCommandLine()
        {
            RepairStandaloneRenderPipelineAssetsInternal();
        }

        private static void RepairStandaloneRenderPipelineAssetsInternal()
        {
            UniversalRenderPipelineAsset pcAsset = LoadRequiredAsset<UniversalRenderPipelineAsset>(PcRpAssetPath);
            UniversalRenderPipelineAsset mobileAsset = LoadRequiredAsset<UniversalRenderPipelineAsset>(MobileRpAssetPath);
            UniversalRenderPipelineAsset standaloneAsset = mobileAsset;
            ScriptableObject pcRenderer = LoadRequiredAsset<ScriptableObject>(PcRendererAssetPath);
            ScriptableObject mobileRenderer = LoadRequiredAsset<ScriptableObject>(MobileRendererAssetPath);
            ScriptableObject globalSettings = LoadRequiredAsset<ScriptableObject>(UrpGlobalSettingsAssetPath);

            GraphicsSettings.defaultRenderPipeline = standaloneAsset;
            QualitySettings.renderPipeline = standaloneAsset;

            TouchUpscalerFields(pcAsset);
            TouchUpscalerFields(mobileAsset);
            TouchRendererXrField(pcRenderer);
            TouchRendererXrField(mobileRenderer);

            EditorUtility.SetDirty(pcAsset);
            EditorUtility.SetDirty(mobileAsset);
            EditorUtility.SetDirty(pcRenderer);
            EditorUtility.SetDirty(mobileRenderer);
            EditorUtility.SetDirty(globalSettings);

            EnsureUrpGlobalSettingsUpgraded();

            AssetDatabase.SaveAssets();
            AssetDatabase.ForceReserializeAssets(
                new List<string>
                {
                    PcRpAssetPath,
                    MobileRpAssetPath,
                    PcRendererAssetPath,
                    MobileRendererAssetPath,
                    UrpGlobalSettingsAssetPath,
                },
                ForceReserializeAssetsOptions.ReserializeAssetsAndMetadata);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            Debug.Log("[GTEX RenderPipelineRepair] Standalone render pipeline assets repaired and reserialized.");
        }

        private static T LoadRequiredAsset<T>(string assetPath) where T : UnityEngine.Object
        {
            T asset = AssetDatabase.LoadAssetAtPath<T>(assetPath);
            if (asset == null)
                throw new InvalidOperationException($"Required asset missing at '{assetPath}'.");

            return asset;
        }

        private static void TouchUpscalerFields(UniversalRenderPipelineAsset asset)
        {
            SerializedObject serializedObject = new SerializedObject(asset);
            serializedObject.UpdateIfRequiredOrScript();

            SerializedProperty iUpscalerName = serializedObject.FindProperty("m_IUpscalerName");
            if (iUpscalerName != null)
                iUpscalerName.stringValue = iUpscalerName.stringValue ?? string.Empty;

            SerializedProperty upscalerOptions = serializedObject.FindProperty("m_UpscalerOptions");
            if (upscalerOptions != null && upscalerOptions.isArray)
                upscalerOptions.arraySize = 0;

            serializedObject.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void TouchRendererXrField(ScriptableObject rendererAsset)
        {
            SerializedObject serializedObject = new SerializedObject(rendererAsset);
            serializedObject.UpdateIfRequiredOrScript();
            SerializedProperty xrSystemData = serializedObject.FindProperty("xrSystemData");
            if (xrSystemData != null && xrSystemData.propertyType == SerializedPropertyType.ObjectReference)
                xrSystemData.objectReferenceValue = xrSystemData.objectReferenceValue;

            serializedObject.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void EnsureUrpGlobalSettingsUpgraded()
        {
            Type globalSettingsType = typeof(UniversalRenderPipelineAsset).Assembly.GetType(
                "UnityEngine.Rendering.Universal.UniversalRenderPipelineGlobalSettings");
            MethodInfo ensureMethod = globalSettingsType?.GetMethod(
                "Ensure",
                BindingFlags.Static | BindingFlags.NonPublic);

            ensureMethod?.Invoke(null, new object[] { true });
        }
    }
}
