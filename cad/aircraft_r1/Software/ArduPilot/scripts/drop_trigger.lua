-- drop_trigger.lua  (ArduPilot Lua, Copter 4.6+/4.7)
-- Programmed in-flight "drop": request an idle-output override for t_cut ms, then
-- hand back to the stock flight mode (AltHold or Loiter), which performs the recovery.
-- Replaces Throw mode, which needs an absolute position (GPS) and recommends >= 10 m drops.
--
-- Why this is better for the paper: the free-fall time before thrust is a SET variable
-- (t_cut) instead of a detection delay that depends on noise; the recovery controller is
-- the unmodified, fixed AltHold/Loiter controller.
--
-- Use:  hover in AltHold (2) or Loiter (5) at the planned height, then set
--         SCR_USER6 = t_cut in ms (50..400)
--       During the cut the motors run at the MOT_SPIN_ARM level (idle, props turning).
--       (SCR_USER1..5 belong to trial_marker.lua.)  The script fires once, logs DROP rows, and resets SCR_USER6 to 0.
-- Safety: refuses if disarmed, in another mode, below DROP_MIN_ALT_M, with no healthy battery
--         monitor, or with the pack below DROP_MIN_V (measured in hover); refuses requests outside 50..400 ms.
--         The override is timed by ArduPilot's servo library, so it ends after t_cut even if this
--         script stalls or crashes.  The kill switch (RC8 = Motor Emergency Stop), a disarm or a
--         mode change is checked by the Lua callback (a forced override would otherwise outrank
--         E-stop for up to t_cut).  When disarmed, ArduPilot's DShot driver always sends 0.
--
-- Mechanism exercised in desktop SITL. Output timing and independent hardware stop require qualification:
--   SRV_Channels:set_output_pwm_chan_timeout() on the Motor1..4 channels.  The motor library
--   stays in THROTTLE_UNLIMITED, so thrust returns the moment the override ends.
--   Do NOT use aux function 31 (Motor Emergency Stop) for the cut: it clears the motor
--   interlock, and on release the motors re-spool from shut-down (~1 s at MOT_SPOOL_TIME 0.5),
--   which in SITL turned a 200 ms cut into ~1.2 s without thrust and 6 m of height loss.

local DROP_MIN_ALT_M = 1.5
-- Pack window, on the MEASURED voltage in hover (not the resting estimate, which depends on a
-- learned resistance).  Worst case the recovery burst adds (37 A - I_hover) x 0.035 Ohm of sag on
-- top of the hover sag: 7.4 V - (37 - 7.4) x 0.035 = 6.36 V >= 6.3 V (Matek H743-MINI V3 minimum);
-- heavier ballast raises I_hover, which only reduces the extra sag.  Also bounds the T/W spread
-- between trials.  T10 / T9-pack confirm the margin.
local DROP_MIN_V = 7.4
local MAX_CUT_MS = 400 -- current desktop-test envelope; hardware use requires qualification
local PERIOD_MS = 5
local MOTOR_FN_FIRST = 33   -- SERVOn_FUNCTION 33..36 = Motor1..Motor4

local state = "idle"
local t_start = 0
local cut_ms = 0
local motor_chans = {}

local function alt_m()
  local d = ahrs:get_relative_position_D_home()
  if d == nil then return nil end
  return -d
end

local function log_drop(event, alt, pwm)
  -- event: 1 = cut start, 2 = release, 3 = refused, 4 = aborted (disarm / mode change)
  logger:write('DROP', 'CutMs,AltM,Event,Pwm', 'IfBH', cut_ms, alt or -1, event, pwm or 0)
end

local function refuse(why)
  gcs:send_text(4, 'DROP refused: ' .. why)
  log_drop(3, alt_m())
  param:set('SCR_USER6', 0)
end

local function find_motors()
  local chans = {}
  for i = 0, 3 do
    local ch = SRV_Channels:find_channel(MOTOR_FN_FIRST + i)
    if ch == nil then return nil end
    chans[#chans + 1] = ch
  end
  return chans
end

local function cut_pwm()
  -- idle = MOT_SPIN_ARM level: props keep turning, so a real ESC needs no restart
  local lo = param:get('MOT_PWM_MIN') or 1000
  local hi = param:get('MOT_PWM_MAX') or 2000
  if lo <= 0 or hi <= lo then lo, hi = 1000, 2000 end
  local arm = param:get('MOT_SPIN_ARM') or 0.1
  return math.floor(lo + arm * (hi - lo))
end

local function override(pwm, ms)
  for _, ch in ipairs(motor_chans) do
    SRV_Channels:set_output_pwm_chan_timeout(ch, pwm, ms)
  end
end

function update()
  local now = millis():toint()
  if state == "idle" then
    local req = param:get('SCR_USER6') or 0
    if req > 0 then
      local mode = vehicle:get_mode()
      local alt = alt_m()
      motor_chans = find_motors()
      if req < 50 or req > MAX_CUT_MS then
        refuse('requested cut outside 50..400 ms test envelope')
      elseif not arming:is_armed() then
        refuse('disarmed')
      elseif mode ~= 2 and mode ~= 5 then
        refuse('mode ' .. tostring(mode) .. ' (need AltHold 2 or Loiter 5)')
      elseif alt == nil or alt < DROP_MIN_ALT_M then
        refuse(string.format('alt %.2f m < %.1f m', alt or -1, DROP_MIN_ALT_M))
      elseif motor_chans == nil then
        refuse('Motor1..4 output channels not found')
      elseif not battery:healthy(0) then
        refuse('battery monitor not healthy')
      elseif battery:voltage(0) < DROP_MIN_V then
        refuse(string.format('pack %.2f V < %.1f V', battery:voltage(0), DROP_MIN_V))
      else
        cut_ms = math.floor(math.min(req, MAX_CUT_MS))
        local pwm = cut_pwm()
        override(pwm, cut_ms)
        t_start = now
        state = "cut"
        log_drop(1, alt, pwm)
        gcs:send_text(5, string.format('DROP cut %d ms at %.2f m (pwm %d)', cut_ms, alt, pwm))
      end
    end
  elseif state == "cut" then
    local mode = vehicle:get_mode()
    -- a forced servo override outranks Motor Emergency Stop, so watch the kill switch ourselves
    local estop = SRV_Channels.get_emergency_stop ~= nil and SRV_Channels:get_emergency_stop()
    if estop or (not arming:is_armed()) or (mode ~= 2 and mode ~= 5) then
      -- end the override now: one loop at stop (DShot 1000 = off), then normal output / E-stop
      override(1000, 1)
      log_drop(4, alt_m())
      gcs:send_text(4, 'DROP aborted (kill switch, disarm or mode change)')
      param:set('SCR_USER6', 0)
      state = "idle"
    elseif now - t_start >= cut_ms then
      -- the servo library has already ended the override; just log it
      local alt = alt_m()
      log_drop(2, alt)
      gcs:send_text(5, string.format('DROP release after %d ms at %.2f m', now - t_start, alt or -1))
      param:set('SCR_USER6', 0)
      state = "idle"
    end
  end
  return update, PERIOD_MS
end

gcs:send_text(6, 'drop_trigger.lua loaded')
return update, PERIOD_MS
