Shader "GTEX/FieldLineOverlay" {
    Properties {
        _MainTex ("Line Mask", 2D) = "black" {}
        _LineColor ("Line Color", Color) = (1, 1, 1, 1)
        _Cutoff ("Cutoff", Range(0, 1)) = 0.08
    }

    SubShader {
        Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" "RenderPipeline" = "UniversalPipeline" }
        Cull Off
        ZWrite On

        Pass {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct Varyings {
                float4 positionHCS : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                half4 _LineColor;
                half _Cutoff;
            CBUFFER_END

            Varyings vert(Attributes input) {
                Varyings output;
                output.positionHCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = TRANSFORM_TEX(input.uv, _MainTex);
                return output;
            }

            half4 frag(Varyings input) : SV_Target {
                half3 sampleRgb = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv).rgb;
                half mask = max(sampleRgb.r, max(sampleRgb.g, sampleRgb.b));
                clip(mask - _Cutoff);
                return _LineColor;
            }
            ENDHLSL
        }
    }
}
