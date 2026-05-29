import { useState } from "react";

interface WorldSpaceProps {
  data: any;
}

export default function WorldSpace({ data }: WorldSpaceProps) {
  const [activeTab, setActiveTab] = useState<"xiaoman" | "user">("xiaoman");

  const xiaoman = data?.xiaoman || {};
  const user = data?.user || {};

  const identity = activeTab === "xiaoman" ? xiaoman.identity : user.identity;
  const living = activeTab === "xiaoman" ? xiaoman.living_env : user.living_env;
  const schedule = activeTab === "xiaoman" ? xiaoman.schedule : user.schedule;
  const emotion = activeTab === "xiaoman" ? xiaoman.emotion : user.emotion;
  const social = activeTab === "xiaoman" ? xiaoman.social : user.social;
  const skills = activeTab === "xiaoman" ? xiaoman.skills : user.skills;

  return (
    <div className="world-space">
      <div className="world-tabs">
        <button
          className={activeTab === "xiaoman" ? "active" : ""}
          onClick={() => setActiveTab("xiaoman")}
        >
          小满的世界
        </button>
        <button
          className={activeTab === "user" ? "active" : ""}
          onClick={() => setActiveTab("user")}
        >
          你的世界
        </button>
      </div>

      <div className="world-content">
        {/* 身份卡片 */}
        {identity && (
          <div className="world-card">
            <h3>身份</h3>
            <div className="world-grid">
              <div><label>名字</label><span>{identity.name || identity.custom_name || "未命名"}</span></div>
              <div><label>年级</label><span>{identity.grade_name || `第${identity.grade}年级`}</span></div>
              {identity.gender && (
                <div><label>性别</label><span>{identity.gender === "female" ? "女" : "男"}</span></div>
              )}
              {identity.school && <div><label>学校</label><span>{identity.school}</span></div>}
              {identity.class && <div><label>班级</label><span>{identity.class}</span></div>}
              {identity.zodiac && <div><label>星座</label><span>{identity.zodiac}</span></div>}
              {identity.catchphrase && <div><label>口头禅</label><span>{identity.catchphrase}</span></div>}
            </div>
            {identity.personality_traits && (
              <div className="traits">
                {Object.entries(identity.personality_traits).map(([k, v]: [string, any]) => (
                  <div key={k} className="trait-bar">
                    <span>{k}</span>
                    <div className="bar"><div style={{ width: `${(v / 10) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 生活环境 */}
        {living && (
          <div className="world-card">
            <h3>生活环境</h3>
            <div className="world-grid">
              {living.city && <div><label>城市</label><span>{living.city}</span></div>}
              {living.housing_type && <div><label>居住</label><span>{living.housing_type}</span></div>}
              {living.room_description && (
                <div className="full-width"><label>房间</label><span>{living.room_description}</span></div>
              )}
              {living.commute && <div><label>通勤</label><span>{living.commute}</span></div>}
              {living.current_weather && <div><label>天气</label><span>{living.current_weather}</span></div>}
              {living.season_preference && <div><label>季节偏好</label><span>{living.season_preference}</span></div>}
            </div>
          </div>
        )}

        {/* 日程 */}
        {schedule && (
          <div className="world-card">
            <h3>日程</h3>
            {schedule.current_activity && (
              <div className="current-status">此刻：{schedule.current_activity}</div>
            )}
            {schedule.daily_routine && (
              <div className="routine-list">
                {Object.entries(schedule.daily_routine).map(([time, activity]: [string, any]) => (
                  <div key={time} className="routine-item">
                    <span className="time">{time}</span>
                    <span className="activity">{activity}</span>
                  </div>
                ))}
              </div>
            )}
            {schedule.countdown?.event && (
              <div className="countdown">
                距离{schedule.countdown.event}还有 {schedule.countdown.days_left} 天
              </div>
            )}
          </div>
        )}

        {/* 情绪 */}
        {emotion && (
          <div className="world-card">
            <h3>情绪状态</h3>
            <div className="emotion-grid">
              <div className="emotion-main">
                <span className="emotion-label">当前</span>
                <span className="emotion-value">{emotion.current_emotion || "平静"}</span>
              </div>
              {emotion.energy !== undefined && (
                <div className="emotion-stat">
                  <label>精力</label>
                  <div className="stat-bar"><div style={{ width: `${emotion.energy}%`, background: "#4CAF50" }} /></div>
                  <span>{emotion.energy}%</span>
                </div>
              )}
              {emotion.security !== undefined && (
                <div className="emotion-stat">
                  <label>安全感</label>
                  <div className="stat-bar"><div style={{ width: `${emotion.security}%`, background: "#2196F3" }} /></div>
                  <span>{emotion.security}%</span>
                </div>
              )}
              {emotion.loneliness !== undefined && (
                <div className="emotion-stat">
                  <label>孤独感</label>
                  <div className="stat-bar"><div style={{ width: `${emotion.loneliness}%`, background: "#FF9800" }} /></div>
                  <span>{emotion.loneliness}%</span>
                </div>
              )}
              {emotion.stress_level !== undefined && (
                <div className="emotion-stat">
                  <label>压力</label>
                  <div className="stat-bar"><div style={{ width: `${emotion.stress_level}%`, background: "#f44336" }} /></div>
                  <span>{emotion.stress_level}%</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 社交关系 */}
        {social && (
          <div className="world-card">
            <h3>社交关系</h3>
            {social.family?.length > 0 && (
              <div className="social-group">
                <h4>家庭</h4>
                {social.family.map((m: any, i: number) => (
                  <div key={i} className="social-item">{m.relation}：{m.detail || m.occupation || ""}</div>
                ))}
              </div>
            )}
            {social.besties?.length > 0 && (
              <div className="social-group">
                <h4>闺蜜/好友</h4>
                {social.besties.map((m: any, i: number) => (
                  <div key={i} className="social-item">{m.name}：{m.trait || m.detail || ""}</div>
                ))}
              </div>
            )}
            {social.deskmate?.description && (
              <div className="social-group">
                <h4>同桌</h4>
                <div className="social-item">{social.deskmate.description}</div>
              </div>
            )}
            {social.pets?.length > 0 && (
              <div className="social-group">
                <h4>宠物</h4>
                {social.pets.map((m: any, i: number) => (
                  <div key={i} className="social-item">{m.name}（{m.type}）：{m.trait || ""}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 技能 */}
        {skills && activeTab === "xiaoman" && (
          <div className="world-card">
            <h3>技能</h3>
            {skills.unlocked?.length > 0 && (
              <div className="skill-group">
                <h4>已解锁</h4>
                {skills.unlocked.map((s: any, i: number) => (
                  <div key={i} className="skill-item">
                    {s.name} Lv.{s.level}/{s.max_level}
                  </div>
                ))}
              </div>
            )}
            {skills.learning?.length > 0 && (
              <div className="skill-group">
                <h4>学习中</h4>
                {skills.learning.map((s: any, i: number) => (
                  <div key={i} className="skill-item">
                    {s.name} ({Math.round((s.progress || 0) * 100)}%)
                  </div>
                ))}
              </div>
            )}
            {skills.knowledge_areas?.length > 0 && (
              <div className="skill-group">
                <h4>知识领域</h4>
                <div className="tag-list">
                  {skills.knowledge_areas.map((a: string, i: number) => (
                    <span key={i} className="tag">{a}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
