using FStudio.Loaders;
using Shared.Responses;
using UnityEngine;
using TMPro;

using System.Linq;
using System.Threading.Tasks;
using FStudio.Database;

namespace FStudio.UI.Events {
    public class ScoreboardScorerMember : MonoBehaviour, IStaticPoolMember<PlayerEntry> {
        [SerializeField] private InteractiveUIElement TargetElement;

        [SerializeField] private TextMeshProUGUI scorerNameText;
        [SerializeField] private TextMeshProUGUI minuteText;

        public bool IsActive { get; set; }
         
        public PlayerEntry Member { get; set; }

        public void MarkAsActive() {
            if (TargetElement != null) {
                TargetElement.Appear();
            }
        }

        public void MarkAsDeactive() {
            if (TargetElement != null) {
                TargetElement.Disappear();
            }
        }

        public void SetMinute (int minute) {
            if (minuteText != null) {
                minuteText.text = minute + "\'";
            }

            if (scorerNameText != null) {
                scorerNameText.text = Member != null ? Member.Name : string.Empty;
            }
        }

#pragma warning disable CS1998
        public async Task SetMember(PlayerEntry member) {
            this.Member = member;
        }
#pragma warning restore CS1998
    }
}
