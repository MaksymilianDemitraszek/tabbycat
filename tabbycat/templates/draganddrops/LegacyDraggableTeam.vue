<template>
  <div draggable=true
       :class="[draggableClasses]"
       @dragstart="dragStart"
       @dragend="dragEnd"
       @mouseenter="showSlideOver(team)"
       @mouseleave="hideSlideOver"><!--
       @mouseenter="show = true"
       @mouseleave="show = false" -->

    <div class="draggable-prefix">
      <h4>{{ team.wins }}</h4>
    </div>
    <div class="draggable-title">
      <h5 class="mt-0 mb-0">{{ titleWithLimit }}</h5>
      <span class="small subtitle">
        <span v-if="team.institution">{{ team.institution.code }}</span>
      </span>
    </div>

  </div>
</template>

<script>
import LegacyDraggableMixin from '../draganddrops/LegacyDraggableMixin.vue'
import SlideOverSubjectMixin from '../info/SlideOverSubjectMixin.vue'
import SlideOverTeamMixin from '../info/SlideOverTeamMixin.vue'

export default {
  mixins: [LegacyDraggableMixin, SlideOverSubjectMixin, SlideOverTeamMixin],
  props: { team: Object, debateId: null, roundInfo: Object },
  computed: {
    titleWithLimit: function () {
      const limit = 15
      if (this.team.short_name.length > limit + 2) {
        return `${this.team.short_name.substring(0, limit)}…`
      }
      return this.team.short_name
    },
    draggablePayload: function () {
      return JSON.stringify({ team: this.team.id, debate: this.debateId })
    },
  },
  methods: {
    handleDragStart: function () {},
    handleDragEnd: function () {},
  },
}
</script>
