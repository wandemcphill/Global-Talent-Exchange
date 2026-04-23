using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Cameras;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacyCameraAdapter
    {
        public bool IsAvailable => CameraSystem.Current != null;

        public bool CanFocusBall => CameraSystem.Current != null && Ball.Current != null;

        public string CurrentCameraType => CameraSystem.Current != null ? CameraSystem.Current.CurrentCameraType : string.Empty;

        public void FocusToBall(bool instant = true)
        {
            if (!CanFocusBall)
            {
                return;
            }

            CameraSystem.Current.FocusToBall(instant);
        }

        public void FocusToPosition(Vector3 position, bool instant = true)
        {
            if (CameraSystem.Current == null)
            {
                return;
            }

            CameraSystem.Current.FocusToPosition(position, instant);
        }

        public void SetTarget(Transform target)
        {
            if (CameraSystem.Current == null || target == null)
            {
                return;
            }

            CameraSystem.Current.SetTarget(target);
        }

        public void SwitchCamera(string cameraType, bool instant = true)
        {
            if (CameraSystem.Current == null || string.IsNullOrWhiteSpace(cameraType))
            {
                return;
            }

            _ = CameraSystem.Current.SwitchCamera(cameraType, instant);
        }
    }
}
