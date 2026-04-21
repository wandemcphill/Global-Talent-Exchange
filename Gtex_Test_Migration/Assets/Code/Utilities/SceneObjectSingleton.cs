using UnityEngine;

namespace FStudio.Utilities {
    public class SceneObjectSingleton<T> : MonoBehaviour where T : Object {
        private static T _Current;
        public static T Current {
            get {
                if (_Current == null) {
                    _Current = Object.FindFirstObjectByType<T>();
                }

                return _Current;
            }
        }

        protected virtual void OnEnable () {
            var instance = this as T;
            if (instance == null) {
                return;
            }

            if (_Current != null && !ReferenceEquals(_Current, instance)) {
                Debug.LogWarning($"{typeof(T)} has multiple instances. It won't break things, but it doesnt sound good tho.");
                return;
            }

            _Current = instance;
        }

        protected virtual void OnDestroy() {
            var instance = this as T;
            if (instance != null && ReferenceEquals(_Current, instance)) {
                _Current = null;
            }
        }
    }
}
