"""
健康管理智能体 · 主界面（Portal）
左侧导航栏 + 右侧内容区（首页 / 个人信息）
"""
import calendar as _calendar
import json
import logging
import re
from datetime import datetime

import gradio as gr

from ui.profile_store import load_profile, save_profile
from ui.health_store import (load_health, save_health, today_str, is_checked_in_today,
                             add_medication, remove_medication, get_unchecked_med_names,
                             add_medical_record, update_medical_record, remove_medical_record,
                             add_chronic_disease, update_chronic_disease, remove_chronic_disease,
                             sync_chronic_meds_to_medications)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

PORTAL_CSS = """
html, body {
    height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}
.gradio-container {
    margin: 0 !important;
    padding: 0 !important;
    height: 100vh !important;
    max-height: 100vh !important;
    max-width: 100vw !important;
    width: 100vw !important;
    overflow: hidden !important;
    font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif !important;
    background: #f0f2f5 !important;
    box-sizing: border-box !important;
}
.main, .app, #root, [data-testid="blocks-container"] {
    margin: 0 !important; padding: 0 !important; gap: 0 !important;
}
[data-testid="blocks-container"] > *, form > * {
    margin: 0 !important; gap: 0 !important;
}
.gradio-container > * { margin: 0 !important; padding: 0 !important; gap: 0 !important; }
.gradio-container > div:first-child {
    display: flex !important; flex-direction: column !important;
    height: 100vh !important; width: 100% !important;
    gap: 0 !important; margin: 0 !important; padding: 0 !important;
}
.gradio-container .block,
.gradio-container .wrap,
.gradio-container .panel,
.gradio-container .gr-group {
    border: none !important; box-shadow: none !important; background: transparent !important;
}

/* Stretch the gr.HTML wrapper that contains the header */
.gradio-container > div:first-child > div:first-child,
.gradio-container > div:first-child > div:first-child > div {
    width: 100vw !important;
    max-width: 100vw !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* === Header === */
.portal-header {
    flex-shrink: 0;
    background: linear-gradient(90deg, #dbeafe 0%, #bfdbfe 50%, #93c5fd 100%);
    color: #1e3a5f;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 32px;
    height: 54px;
    margin: 0;
    border-radius: 0;
    width: 100vw !important;
    max-width: 100vw !important;
    box-sizing: border-box !important;
    user-select: none;
    border-bottom: 1px solid #93c5fd;
}
.portal-header-icon { font-size: 1.5em; }
.portal-header h1 { margin: 0; font-size: 1.1em; font-weight: 700; letter-spacing: 0.3px; color: #1e3a5f; }
.portal-header-sub { margin: 0; font-size: 0.7em; color: #3b6fa0; }

/* === Body row === */
.portal-body-row {
    flex: 1 !important;
    height: calc(100vh - 54px) !important;
    max-height: calc(100vh - 54px) !important;
    overflow: hidden !important;
    gap: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    align-items: stretch !important;
}
/* Let each direct child manage its own overflow */
.portal-body-row > * {
    height: calc(100vh - 54px) !important;
    max-height: calc(100vh - 54px) !important;
    min-height: 0 !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
}

/* === Sidebar column === */
.portal-sidebar-col {
    background: #f0f4fa !important;
    border-right: 1px solid #d8e4f0 !important;
    border-radius: 12px 0 0 12px !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    flex-shrink: 0 !important;
    max-width: 210px !important;
    min-width: 190px !important;
    width: 200px !important;
    margin-left: 16px !important;
    margin-top: 16px !important;
    margin-bottom: 16px !important;
    height: calc(100vh - 86px) !important;
    max-height: calc(100vh - 86px) !important;
    box-shadow: 2px 0 8px rgba(45,95,158,0.06) !important;
}
.portal-sidebar-col > * { background: transparent !important; }

.sidebar-section-label {
    font-size: 0.62em;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #8aaac8;
    padding: 18px 18px 6px;
    margin: 0;
}
.sidebar-sep {
    height: 1px;
    background: #d0dcea;
    margin: 8px 14px;
}

/* === Sidebar nav buttons — use descendant "button" (no intermediate div in Gradio 6) === */
.nav-btn, .nav-btn-active, .nav-btn-disabled {
    padding: 0 10px !important;
    margin: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
.nav-btn button,
.nav-btn-active button,
.nav-btn-disabled button {
    width: auto !important;
    min-width: 0 !important;
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    outline: none !important;
    text-align: left !important;
    padding: 7px 14px !important;
    margin: 2px 0 !important;
    font-size: 0.85em !important;
    color: #4a6580 !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    justify-content: flex-start !important;
    gap: 8px !important;
    white-space: nowrap !important;
}
.nav-btn button:hover {
    background: rgba(45,95,158,0.08) !important;
    color: #2d5f9e !important;
}
/* Active nav item — soft blue highlight */
.nav-btn-active button {
    background: rgba(45,95,158,0.1) !important;
    color: #2d5f9e !important;
    font-weight: 600 !important;
}
/* Disabled nav item */
.nav-btn-disabled button {
    opacity: 0.4 !important;
    cursor: not-allowed !important;
    pointer-events: none !important;
}

/* === Content column === */
.portal-content-col {
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 0 !important;
    background: #eef0f4 !important;
    flex: 1 !important;
    min-width: 0 !important;
}
.portal-content-col > * { background: transparent !important; }

/* === Content panels === */
.content-panel {
    padding: 24px 32px !important;
    box-sizing: border-box !important;
    min-height: 0 !important;
    width: 100% !important;
}
/* Extra bottom breathing room for module panels */
.module-panel-bottom { height: 48px; flex-shrink: 0; }

/* === HOME PANEL === */
.home-layout {
    display: flex;
    gap: 28px;
    align-items: flex-start;
    margin-bottom: 28px;
}

/* Robot scene */
.robot-scene {
    flex-shrink: 0;
    width: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 20px;
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
}
@keyframes glow-pulse {
    0%, 100% { box-shadow: 0 0 6px #4fc3f7, 0 0 12px rgba(79,195,247,0.3); opacity: 0.8; }
    50% { box-shadow: 0 0 14px #4fc3f7, 0 0 28px rgba(79,195,247,0.6); opacity: 1; }
}
@keyframes eye-blink {
    0%, 88%, 92%, 100% { transform: scaleY(1); }
    90% { transform: scaleY(0.08); }
}
@keyframes core-pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.18); }
}
@keyframes antenna-blink {
    0%, 55%, 100% { background: #4fc3f7; box-shadow: 0 0 8px #4fc3f7; }
    60%, 70% { background: #fff; box-shadow: 0 0 4px #fff; }
    65% { background: transparent; box-shadow: none; }
}
@keyframes scan-line {
    0% { width: 0; opacity: 0; margin-left: 0; }
    20% { opacity: 1; }
    80% { opacity: 1; }
    100% { width: 44px; opacity: 0; margin-left: 0; }
}
@keyframes bg-rotate {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes platform-pulse {
    0%, 100% { opacity: 0.3; transform: scaleX(1); }
    50% { opacity: 0.7; transform: scaleX(1.15); }
}

.robot-float { animation: float 3.2s ease-in-out infinite; position: relative; }

.robot-bg-ring {
    position: absolute;
    width: 130px; height: 130px;
    border-radius: 50%;
    border: 1px solid rgba(79,195,247,0.15);
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    animation: bg-rotate 8s linear infinite;
}
.robot-bg-ring::before {
    content: "";
    position: absolute;
    width: 6px; height: 6px;
    background: #4fc3f7;
    border-radius: 50%;
    top: -3px; left: 50%;
    margin-left: -3px;
    box-shadow: 0 0 6px #4fc3f7;
}

.robot-antenna-ball {
    width: 10px; height: 10px;
    background: #4fc3f7;
    border-radius: 50%;
    margin: 0 auto 0;
    animation: antenna-blink 1.4s ease-in-out infinite;
}
.robot-antenna-stick {
    width: 2px; height: 18px;
    background: rgba(79,195,247,0.5);
    margin: 0 auto;
}

.robot-head {
    width: 74px; height: 58px;
    background: linear-gradient(155deg, #1a3050 0%, #1f4070 100%);
    border-radius: 10px;
    border: 1.5px solid #4fc3f7;
    box-shadow: 0 0 12px rgba(79,195,247,0.25), inset 0 1px 0 rgba(255,255,255,0.07);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 7px;
    position: relative;
    overflow: hidden;
}
.robot-eyes { display: flex; gap: 16px; }
.robot-eye {
    width: 14px; height: 14px;
    background: #4fc3f7;
    border-radius: 50%;
    animation: glow-pulse 2s ease-in-out infinite, eye-blink 5s ease-in-out infinite;
}
.robot-eye:last-child { animation-delay: 0.3s, 0.3s; }
.robot-scan-bar {
    height: 2px;
    background: linear-gradient(90deg, transparent, #4fc3f7, transparent);
    border-radius: 1px;
    animation: scan-line 2.4s ease-in-out infinite;
}

.robot-neck {
    width: 20px; height: 8px;
    background: linear-gradient(135deg, #152840, #1f4070);
    border-left: 1.5px solid rgba(79,195,247,0.4);
    border-right: 1.5px solid rgba(79,195,247,0.4);
    margin: 0 auto;
}

.robot-body {
    width: 86px; height: 72px;
    background: linear-gradient(155deg, #1a3050 0%, #1f4070 100%);
    border-radius: 8px;
    border: 1.5px solid rgba(79,195,247,0.5);
    box-shadow: 0 0 10px rgba(79,195,247,0.1);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    position: relative;
}
.robot-core {
    width: 24px; height: 24px;
    background: radial-gradient(circle, #81d4fa 0%, #0288d1 50%, #01579b 100%);
    border-radius: 50%;
    animation: core-pulse 1.6s ease-in-out infinite;
    box-shadow: 0 0 12px #4fc3f7, 0 0 24px rgba(79,195,247,0.4);
}
.robot-rib {
    width: 52px; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(79,195,247,0.35), transparent);
    border-radius: 1px;
}
.robot-rib.short { width: 36px; }

.robot-arms {
    position: absolute;
    top: 10px;
    display: flex;
    gap: 100px;
}
.robot-arm {
    width: 10px; height: 44px;
    background: linear-gradient(135deg, #152840, #1f4070);
    border-radius: 5px;
    border: 1.5px solid rgba(79,195,247,0.35);
}

.robot-legs {
    display: flex;
    gap: 14px;
    margin-top: 0;
}
.robot-leg {
    width: 20px; height: 24px;
    background: linear-gradient(135deg, #152840, #1f4070);
    border-radius: 0 0 5px 5px;
    border: 1.5px solid rgba(79,195,247,0.4);
    border-top: none;
}

.robot-platform {
    width: 110px; height: 6px;
    background: linear-gradient(90deg, transparent, rgba(79,195,247,0.4), transparent);
    border-radius: 50%;
    margin-top: 6px;
    animation: platform-pulse 2s ease-in-out infinite;
}

.robot-label {
    font-size: 0.8em;
    color: #4fc3f7;
    font-weight: 600;
    margin-top: 14px;
    letter-spacing: 1px;
    text-align: center;
}
.robot-sublabel {
    font-size: 0.68em;
    color: rgba(79,195,247,0.5);
    margin-top: 2px;
    text-align: center;
}

/* === Home row layout === */
.home-row {
    gap: 20px !important;
    align-items: stretch !important;
    margin-bottom: 0 !important;
    flex-wrap: nowrap !important;
}
.home-left-col {
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    background: transparent !important;
    min-width: 0 !important;
}
.robot-col {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    padding-top: 16px !important;
    min-width: 0 !important;
    background: transparent !important;
}
.news-gr-col {
    min-width: 0 !important;
    background: transparent !important;
}

/* === News title row + refresh button === */
.news-title-row {
    align-items: center !important;
    margin-bottom: 14px !important;
    gap: 10px !important;
}
.news-title-row > * { background: transparent !important; }
.news-section-head {
    flex: 1;
    font-size: 1.05em;
    font-weight: 700;
    color: #1a3c6e;
    margin: 0;
}
.btn-refresh-news, .btn-refresh-news button {
    background: transparent !important;
    border: 1px solid #c8d8ee !important;
    border-radius: 6px !important;
    color: #5a7fa8 !important;
    font-size: 0.78em !important;
    padding: 4px 12px !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    box-shadow: none !important;
    white-space: nowrap !important;
    width: auto !important;
}
.btn-refresh-news button:hover {
    background: #eef3fb !important;
    border-color: #2d5f9e !important;
    color: #2d5f9e !important;
}

/* === News feed === */
.news-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0;
    min-width: 0;
}
.news-title {
    font-size: 1.05em;
    font-weight: 700;
    color: #1a3c6e;
    margin: 0 0 14px;
}
.news-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 20px;
    background: #fff;
    border-radius: 12px;
    border: 1px solid #e8ecf2;
    color: #8a96a6;
    font-size: 0.88em;
}
@keyframes spin {
    to { transform: rotate(360deg); }
}
.news-spinner {
    width: 18px; height: 18px;
    border: 2px solid #e0e6f0;
    border-top-color: #2d5f9e;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
.news-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
}
.news-card {
    background: #fff;
    border-radius: 10px;
    padding: 16px 18px;
    border: 1px solid #d4d9e2;
    border-left: 3px solid #2d5f9e;
    transition: box-shadow 0.2s, transform 0.2s;
}
.news-card:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.07);
    transform: translateY(-2px);
}
.news-card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}
.news-card-icon { font-size: 1.2em; }
.news-tag {
    font-size: 0.6em;
    padding: 2px 7px;
    border-radius: 8px;
    font-weight: 600;
}
.tag-diet   { background: #fff3e0; color: #e65100; }
.tag-ep     { background: #fce4ec; color: #c62828; }
.tag-season { background: #e8f5e9; color: #2e7d32; }
.tag-sci    { background: #e3f2fd; color: #1565c0; }
.tag-misc   { background: #f3e5f5; color: #7b1fa2; }
.news-card-title {
    font-size: 0.92em;
    font-weight: 600;
    color: #1a3c6e;
    margin: 0 0 5px;
    line-height: 1.4;
}
.news-card-body {
    font-size: 0.79em;
    color: #6b7b8d;
    line-height: 1.6;
    margin: 0;
}

/* === PROFILE PANEL === */
.profile-header {
    margin-bottom: 22px;
}
.profile-header h2 {
    font-size: 1.3em;
    font-weight: 700;
    color: #1a3c6e;
    margin: 0 0 4px;
}
.profile-header p {
    font-size: 0.82em;
    color: #8a96a6;
    margin: 0;
}
.profile-form-card {
    background: #fff !important;
    border-radius: 12px !important;
    padding: 24px 28px !important;
    border: 1px solid #d4d9e2 !important;
    border-top: 3px solid #2d5f9e !important;
    max-width: 680px !important;
    box-shadow: 0 2px 8px rgba(45,95,158,0.06) !important;
}
.profile-form-card .info-input input,
.profile-form-card .info-input select,
.profile-form-card .info-input textarea {
    border: 1px solid #ccd2db !important;
    border-radius: 6px !important;
    background: #fafbfc !important;
    font-size: 0.85em !important;
    padding: 6px 10px !important;
    transition: border 0.15s !important;
}
.profile-form-card .info-input input:focus,
.profile-form-card .info-input textarea:focus {
    border-color: #4a7fc1 !important;
    box-shadow: 0 0 0 2px rgba(74,127,193,0.12) !important;
    outline: none !important;
}
.profile-form-card .gender-radio label {
    font-size: 0.84em !important;
    padding: 5px 14px !important;
    border: 1px solid #ccd2db !important;
    border-radius: 6px !important;
    background: #fafbfc !important;
    cursor: pointer !important;
    transition: all 0.12s !important;
}
.profile-form-card .gender-radio label:has(input:checked) {
    background: #2d5f9e !important;
    color: #fff !important;
    border-color: #2d5f9e !important;
}
.profile-form-card .gender-radio .wrap { gap: 8px !important; flex-wrap: nowrap !important; }
.btn-save, .btn-save button {
    background: #2d5f9e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.9em !important;
    font-weight: 600 !important;
    padding: 9px 28px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    margin-top: 4px !important;
}
.btn-save:hover, .btn-save button:hover { background: #245089 !important; }
.save-ok { font-size: 0.8em; color: #2e7d32; margin-left: 8px; }

/* === Exit button === */
.nav-btn-exit, .nav-btn-exit button {
    background: transparent !important;
    border: none !important;
    border-top: 1px solid #d0dcea !important;
    border-left: 3px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    width: 100% !important;
    text-align: left !important;
    padding: 10px 16px 10px 15px !important;
    font-size: 0.88em !important;
    color: #c0504a !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    justify-content: flex-start !important;
    gap: 10px !important;
    margin-top: 8px !important;
}
.nav-btn-exit button:hover {
    background: rgba(192,80,74,0.08) !important;
    color: #a83832 !important;
    border-left-color: #c0504a !important;
}
/* Exit status text */
.nav-btn-exit + div { background: transparent !important; border: none !important; padding: 0 !important; }

/* Footer */
.portal-footer {
    text-align: center;
    color: #b0b8c6;
    font-size: 0.68em;
    padding: 20px 0 8px;
}

/* === Home chat (health assistant) === */
.home-chat-col {
    background: transparent !important;
    min-width: 0 !important;
}
.home-chat-header {
    font-size: 0.95em;
    font-weight: 700;
    color: #1a3c6e;
    margin: 0 0 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.home-chat-sub {
    font-size: 0.75em;
    color: #8a96a6;
    margin: 0 0 10px;
}
.home-chat-wrap {
    background: #fff !important;
    border: 1px solid #d4d9e2 !important;
    border-radius: 12px !important;
    padding: 10px !important;
    box-shadow: 0 2px 8px rgba(45,95,158,0.05) !important;
}
.home-chat-wrap .chatbot {
    min-height: 260px !important;
    max-height: 360px !important;
}
.home-chat-input-row {
    gap: 8px !important;
    margin-top: 6px !important;
}
.home-chat-input-row > * { background: transparent !important; }
.btn-home-send, .btn-home-send button {
    background: #2d5f9e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.85em !important;
    font-weight: 600 !important;
    padding: 8px 18px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    white-space: nowrap !important;
}
.btn-home-send button:hover { background: #245089 !important; }
.btn-home-clear, .btn-home-clear button {
    background: transparent !important;
    color: #8a96a6 !important;
    border: 1px solid #d4d9e2 !important;
    border-radius: 8px !important;
    font-size: 0.8em !important;
    padding: 8px 12px !important;
    cursor: pointer !important;
    white-space: nowrap !important;
}
.btn-home-clear button:hover { background: #f5f7fa !important; color: #5a6a7a !important; }

/* === Exercise reminder === */
.exercise-reminder {
    background: linear-gradient(90deg, #fff8e1, #fffde7);
    border: 1px solid #ffe082;
    border-left: 4px solid #f9a825;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 0.88em;
    color: #7a5c00;
    margin-bottom: 14px;
    font-weight: 500;
}

/* === Module panel cards === */
.module-header { margin-bottom: 20px; }
.module-header h2 { font-size: 1.3em; font-weight: 700; color: #1a3c6e; margin: 0 0 4px; }
.module-header p { font-size: 0.82em; color: #8a96a6; margin: 0; }

.plan-card {
    background: #fff;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #d4d9e2;
    border-top: 3px solid #2d5f9e;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(45,95,158,0.06);
    white-space: pre-wrap;
    line-height: 1.8;
    font-size: 0.88em;
    color: #333;
    max-height: 340px;
    overflow-y: auto;
}
.plan-meta {
    font-size: 0.72em;
    color: #9aa5b4;
    margin-bottom: 10px;
}

/* === Action buttons (generate/refresh) === */
.btn-action, .btn-action button {
    background: #2d5f9e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.88em !important;
    font-weight: 600 !important;
    padding: 8px 22px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    box-shadow: none !important;
    white-space: nowrap !important;
    width: auto !important;
}
.btn-action button:hover { background: #245089 !important; }
.btn-action-outline, .btn-action-outline button {
    background: transparent !important;
    color: #2d5f9e !important;
    border: 1px solid #2d5f9e !important;
    border-radius: 8px !important;
    font-size: 0.88em !important;
    font-weight: 600 !important;
    padding: 8px 22px !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    box-shadow: none !important;
    width: auto !important;
}
.btn-action-outline button:hover {
    background: rgba(45,95,158,0.07) !important;
}

/* === Calendar === */
.cal-section { margin-bottom: 20px; }
.cal-nav-row { align-items: center !important; gap: 8px !important; margin-bottom: 10px !important; }
.cal-nav-row > * { background: transparent !important; }
.cal-month-label {
    text-align: center;
    font-size: 1em;
    font-weight: 700;
    color: #1a3c6e;
    flex: 1;
    margin: 0;
}
.btn-cal-nav, .btn-cal-nav button {
    background: transparent !important;
    border: 1px solid #c8d8ee !important;
    border-radius: 6px !important;
    color: #5a7fa8 !important;
    font-size: 0.85em !important;
    padding: 4px 10px !important;
    cursor: pointer !important;
    box-shadow: none !important;
    width: auto !important;
    transition: all 0.15s !important;
}
.btn-cal-nav button:hover { background: #eef3fb !important; color: #2d5f9e !important; }

.cal-html-wrap {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #d4d9e2;
    box-shadow: 0 2px 6px rgba(45,95,158,0.05);
}
.cal-stats {
    font-size: 0.82em;
    color: #5a7fa8;
    margin-bottom: 12px;
    font-weight: 500;
}
.cal-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85em;
}
.cal-table th {
    text-align: center;
    padding: 4px 0;
    font-weight: 600;
    color: #8aaac8;
    font-size: 0.8em;
}
.cal-table td { text-align: center; padding: 5px 2px; }
.cal-day {
    width: 32px; height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: #4a6580;
    font-size: 0.9em;
    cursor: default;
    line-height: 1;
}
.cal-today { background: #e8f0fa; color: #2d5f9e; font-weight: 700; }
.cal-checked { background: #e8f5e9 !important; color: #2e7d32 !important; }
.cal-checked::after { content: "✓"; font-size: 0.6em; display: block; margin-top: -2px; }
.cal-empty { }

.btn-checkin, .btn-checkin button {
    background: #43a047 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.9em !important;
    font-weight: 600 !important;
    padding: 9px 28px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    box-shadow: none !important;
    width: auto !important;
}
.btn-checkin button:hover { background: #388e3c !important; }
.btn-checkin-done, .btn-checkin-done button {
    background: #a5d6a7 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.9em !important;
    padding: 9px 28px !important;
    cursor: default !important;
    box-shadow: none !important;
    width: auto !important;
}

/* === Sleep log === */
.sleep-form-card {
    background: #fff;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #d4d9e2;
    border-top: 3px solid #2d5f9e;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(45,95,158,0.06);
    max-width: 680px;
}
.sleep-log-wrap {
    background: #fff;
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid #d4d9e2;
    box-shadow: 0 2px 6px rgba(45,95,158,0.05);
    max-height: 260px;
    overflow-y: auto;
}
.sleep-log-entry {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #f0f2f5;
    font-size: 0.84em;
    color: #4a6580;
}
.sleep-log-entry:last-child { border-bottom: none; }
.sleep-del-btn {
    margin-left: auto;
    color: #c0504a;
    font-size: 1.1em;
    font-weight: 700;
    cursor: pointer;
    padding: 0 6px;
    border-radius: 4px;
    line-height: 1;
    opacity: 0.4;
    transition: opacity 0.15s;
    user-select: none;
    flex-shrink: 0;
}
.sleep-del-btn:hover { opacity: 1; background: #fce4e4; }
/* CSS-visible but zero-height so JS can reach the DOM node */
.sleep-del-hidden {
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
.sleep-del-hidden * {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}
.sleep-log-date { font-weight: 600; color: #1a3c6e; min-width: 80px; }
.sleep-quality-stars { color: #f9a825; }
.sleep-eval-card {
    background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
    border-radius: 10px;
    padding: 16px 20px;
    border: 1px solid #c8e6c9;
    font-size: 0.87em;
    color: #2e5c1e;
    line-height: 1.75;
    white-space: pre-wrap;
    max-height: 220px;
    overflow-y: auto;
}

/* === Mood record === */
.mood-dot-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.mood-dot {
    width: 28px; height: 28px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.65em; color: #fff; font-weight: 700;
    cursor: default; position: relative;
}
.mood-dot:hover::after {
    content: attr(title); position: absolute; bottom: 32px; left: 50%;
    transform: translateX(-50%); background: #333; color: #fff;
    font-size: 10px; padding: 2px 6px; border-radius: 4px; white-space: nowrap;
}
.mood-1 { background: #ef5350; }
.mood-2 { background: #ff8f00; }
.mood-3 { background: #aab828; }
.mood-4 { background: #43a047; }
.mood-5 { background: #1565c0; }
.mood-rec-list { margin-top: 10px; display: flex; flex-direction: column; gap: 5px; }
.mood-rec-row {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 10px; background: #fff; border: 1px solid #e8ecf2;
    border-radius: 8px; font-size: 0.82em;
}
.mood-rec-date { color: #5a7fa8; font-weight: 600; min-width: 80px; }
.mood-rec-emoji { font-size: 1.1em; }
.mood-rec-label { font-weight: 600; min-width: 36px; }
.mood-rec-label.mood-1 { background: none; color: #ef5350; }
.mood-rec-label.mood-2 { background: none; color: #ff8f00; }
.mood-rec-label.mood-3 { background: none; color: #aab828; }
.mood-rec-label.mood-4 { background: none; color: #43a047; }
.mood-rec-label.mood-5 { background: none; color: #1565c0; }
.mood-rec-note { color: #6b7b8d; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mood-rec-del {
    color: #c0504a; cursor: pointer; font-size: 1.2em; font-weight: 700;
    margin-left: auto; padding: 0 4px; border-radius: 4px; transition: background 0.12s;
}
.mood-rec-del:hover { background: rgba(192,80,74,0.1); }

/* === Mental chatbot === */
.mental-chat-wrap .wrap { background: #fff !important; border: 1px solid #d4d9e2 !important; border-radius: 12px !important; }
.mental-input-row { gap: 8px !important; align-items: flex-end !important; }

/* === Medication panel === */
.med-list-card {
    background: #fff; border-radius: 12px; padding: 14px 18px;
    border: 1px solid #d4d9e2; margin-bottom: 14px;
    box-shadow: 0 2px 6px rgba(45,95,158,0.05);
}
.med-row {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 0; border-bottom: 1px solid #f0f2f5;
    font-size: 0.84em; color: #4a6580;
}
.med-row:last-child { border-bottom: none; }
.med-name { font-weight: 600; color: #1a3c6e; min-width: 80px; }
.med-dosage { color: #5a7fa8; font-size: 0.9em; }
.med-times { font-size: 0.78em; color: #8aaac8; }
.med-taken { color: #43a047; font-weight: 600; }
.med-reminder {
    background: linear-gradient(90deg, #fff3e0, #fce4ec);
    border: 1px solid #ffcc80; border-left: 4px solid #fb8c00;
    border-radius: 8px; padding: 10px 16px;
    font-size: 0.88em; color: #7a3800;
    margin-bottom: 14px; font-weight: 500;
}
.med-add-form {
    background: #fff; border-radius: 12px; padding: 16px 20px;
    border: 1px solid #d4d9e2; border-top: 3px solid #2d5f9e;
    box-shadow: 0 2px 8px rgba(45,95,158,0.06);
}
.checkin-card {
    background: #fff; border-radius: 12px; padding: 16px 20px;
    border: 1px solid #d4d9e2; margin-bottom: 14px;
    box-shadow: 0 2px 6px rgba(45,95,158,0.05);
}

/* === Medical records panel === */
.medrec-card {
    background: #fff; border-radius: 10px; padding: 14px 18px;
    border: 1px solid #d4d9e2; border-left: 3px solid #5a7fa8;
    margin-bottom: 10px; position: relative;
    box-shadow: 0 1px 4px rgba(45,95,158,0.05);
    transition: box-shadow 0.15s;
}
.medrec-card:hover { box-shadow: 0 3px 10px rgba(45,95,158,0.1); }
.medrec-top { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.medrec-date { font-size: 0.78em; color: #5a7fa8; font-weight: 600; }
.medrec-source {
    font-size: 0.68em; padding: 1px 8px; border-radius: 10px; font-weight: 600;
}
.medrec-source-manual { background: #e3f2fd; color: #1565c0; }
.medrec-source-ai { background: #fce4ec; color: #c62828; }
.medrec-symptom { font-size: 0.9em; font-weight: 600; color: #1a3c6e; margin-bottom: 4px; }
.medrec-detail { font-size: 0.8em; color: #6b7b8d; line-height: 1.6; }
.medrec-detail b { color: #4a6580; font-weight: 600; }
.medrec-actions {
    position: absolute; top: 10px; right: 12px;
    display: flex; gap: 8px; align-items: center;
}
.medrec-btn-edit, .medrec-btn-del {
    cursor: pointer; font-size: 0.82em; padding: 2px 6px;
    border-radius: 4px; transition: background 0.12s;
}
.medrec-btn-edit { color: #2d5f9e; }
.medrec-btn-edit:hover { background: rgba(45,95,158,0.1); }
.medrec-btn-del { color: #c0504a; font-weight: 700; }
.medrec-btn-del:hover { background: rgba(192,80,74,0.1); }
.medrec-empty {
    color: #9aa5b4; font-size: 0.85em; text-align: center; padding: 30px 0;
}
.medrec-form-card {
    background: #fff; border-radius: 12px; padding: 18px 22px;
    border: 1px solid #d4d9e2; border-top: 3px solid #2d5f9e;
    box-shadow: 0 2px 8px rgba(45,95,158,0.06);
    margin-bottom: 14px;
}

/* === Chronic disease panel === */
.chronic-card {
    background: #fff; border-radius: 10px; padding: 16px 18px;
    border: 1px solid #d4d9e2; border-left: 3px solid #e65100;
    margin-bottom: 10px; position: relative;
    box-shadow: 0 1px 4px rgba(45,95,158,0.05);
}
.chronic-card:hover { box-shadow: 0 3px 10px rgba(45,95,158,0.1); }
.chronic-top { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.chronic-name { font-size: 0.95em; font-weight: 700; color: #1a3c6e; }
.chronic-date { font-size: 0.75em; color: #8aaac8; }
.chronic-section { font-size: 0.8em; color: #4a6580; margin-top: 6px; line-height: 1.6; }
.chronic-section b { color: #1a3c6e; font-weight: 600; }
.chronic-tag {
    display: inline-block; font-size: 0.68em; padding: 1px 8px; border-radius: 10px;
    font-weight: 600; background: #fff3e0; color: #e65100; margin-left: 6px;
}
.chronic-med-link {
    font-size: 0.72em; color: #2d5f9e; text-decoration: underline; cursor: default;
}
.chronic-actions {
    position: absolute; top: 12px; right: 12px;
    display: flex; gap: 8px; align-items: center;
}
.chronic-btn-edit, .chronic-btn-del {
    cursor: pointer; font-size: 0.82em; padding: 2px 6px;
    border-radius: 4px; transition: background 0.12s;
}
.chronic-btn-edit { color: #2d5f9e; }
.chronic-btn-edit:hover { background: rgba(45,95,158,0.1); }
.chronic-btn-del { color: #c0504a; font-weight: 700; }
.chronic-btn-del:hover { background: rgba(192,80,74,0.1); }
.chronic-empty { color: #9aa5b4; font-size: 0.85em; text-align: center; padding: 30px 0; }
.chronic-form-card {
    background: #fff; border-radius: 12px; padding: 18px 22px;
    border: 1px solid #d4d9e2; border-top: 3px solid #e65100;
    box-shadow: 0 2px 8px rgba(45,95,158,0.06); margin-bottom: 14px;
}
.chronic-sub-list { margin: 4px 0 0 12px; }
.chronic-sub-item {
    font-size: 0.78em; color: #6b7b8d; padding: 2px 0;
    display: flex; align-items: center; gap: 6px;
}
.chronic-sub-item .dot { width: 5px; height: 5px; border-radius: 50%; background: #e65100; flex-shrink: 0; }
"""

# ---------------------------------------------------------------------------
# Robot HTML
# ---------------------------------------------------------------------------

ROBOT_HTML = """
<div class="robot-scene">
  <div class="robot-float">
    <div class="robot-bg-ring"></div>
    <div class="robot-antenna-ball"></div>
    <div class="robot-antenna-stick"></div>
    <div class="robot-head">
      <div class="robot-eyes">
        <div class="robot-eye"></div>
        <div class="robot-eye"></div>
      </div>
      <div class="robot-scan-bar"></div>
    </div>
    <div class="robot-neck"></div>
    <div class="robot-body">
      <div class="robot-arms"><div class="robot-arm"></div><div class="robot-arm"></div></div>
      <div class="robot-core"></div>
      <div class="robot-rib"></div>
      <div class="robot-rib short"></div>
    </div>
    <div class="robot-legs">
      <div class="robot-leg"></div>
      <div class="robot-leg"></div>
    </div>
  </div>
  <div class="robot-platform"></div>
  <p class="robot-label">AI 健康助手</p>
  <p class="robot-sublabel">powered by MedAgents</p>
</div>
"""

# ---------------------------------------------------------------------------
# Tag mapping for LLM-returned categories
# ---------------------------------------------------------------------------
TAG_CLASS_MAP = {
    "饮食":    ("tag-diet",   "🥦"),
    "膳食":    ("tag-diet",   "🥗"),
    "流行病":  ("tag-ep",    "🦠"),
    "预防":    ("tag-ep",    "🛡️"),
    "季节":    ("tag-season","🌿"),
    "医学":    ("tag-sci",   "🔬"),
    "科普":    ("tag-sci",   "📖"),
}

STATIC_NEWS = [
    {"icon": "🥦", "tag": "饮食建议",  "tag_class": "tag-diet",
     "title": "春季饮食调养建议",
     "body": "春季肝气旺盛，宜多食绿色蔬菜如菠菜、芹菜，少食辛辣，适量补充维生素C，有助于提高免疫力，预防春季感冒。"},
    {"icon": "🦠", "tag": "流行病预防", "tag_class": "tag-ep",
     "title": "流感高峰期防护要点",
     "body": "当前流感活跃，请保持手卫生，咳嗽打喷嚏时用纸巾遮挡，密闭空间戴口罩。老人、儿童及慢病患者建议接种流感疫苗。"},
    {"icon": "🌿", "tag": "季节健康",  "tag_class": "tag-season",
     "title": "换季过敏性鼻炎应对",
     "body": "花粉季节外出建议佩戴口罩，回家后及时洗手洗脸，避免揉眼。室内可使用空气净化器，症状严重者及时就医。"},
    {"icon": "🔬", "tag": "医学科普",  "tag_class": "tag-sci",
     "title": "血压的正确测量方法",
     "body": "测血压前休息5分钟，取坐位，手臂与心脏同高，不说话不动弹。早晚各测一次，取平均值，连续记录7天更有参考价值。"},
    {"icon": "💧", "tag": "健康小知识", "tag_class": "tag-misc",
     "title": "正确补水，从清晨开始",
     "body": "晨起空腹喝一杯温水（200mL）可激活代谢、促进肠胃蠕动。全天饮水量建议1500-1700mL，运动或出汗多时适量增加。"},
    {"icon": "😴", "tag": "睡眠健康",  "tag_class": "tag-misc",
     "title": "22点前入睡的益处",
     "body": "晚上10点至凌晨2点是生长激素分泌高峰期，此阶段深度睡眠有助于细胞修复、免疫强化。建议固定就寝时间，避免熬夜。"},
]


def _render_news_html(items: list[dict]) -> str:
    cards = []
    for item in items:
        icon = item.get("icon", "💊")
        tag  = item.get("category", item.get("tag", "健康"))
        title = item.get("title", "")
        body  = item.get("content", item.get("body", ""))
        # pick tag class
        cls = "tag-misc"
        for k, (c, _) in TAG_CLASS_MAP.items():
            if k in tag:
                cls = c
                break
        cards.append(f"""
        <div class="news-card">
          <div class="news-card-header">
            <span class="news-card-icon">{icon}</span>
            <span class="news-tag {cls}">{tag}</span>
          </div>
          <p class="news-card-title">{title}</p>
          <p class="news-card-body">{body}</p>
        </div>""")
    return '<div class="news-grid">' + "".join(cards) + "</div>"


def _static_news_html() -> str:
    return _render_news_html([
        {"icon": s["icon"], "category": s["tag"], "title": s["title"], "content": s["body"]}
        for s in STATIC_NEWS
    ])


async def _fetch_ai_news(llm) -> str:
    """Call LLM to generate today's health news. Falls back to static on error."""
    today = datetime.now()
    month = today.month
    season_map = {1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春",
                  6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋",
                  11: "秋", 12: "冬"}
    season = season_map.get(month, "春")
    date_str = today.strftime("%Y年%m月%d日")

    prompt = f"""你是一个专业健康资讯编辑。请生成6条今日健康资讯推送，内容覆盖：
1. 饮食建议（当前{season}季饮食调养，1条）
2. 流行病预防（{month}月常见传染病或流行病，1条）
3. 季节性疾病（{season}季常见疾病预防应对，1条）
4. 医学科普（一个实用的医学知识，1条）
5. 健康生活方式（运动/睡眠/心理，1条）
6. 急救或用药常识（1条）

当前日期：{date_str}
要求：每条标题15字以内，内容60-90字，生动实用，用二三人称。
返回严格JSON格式：
{{"items":[{{"icon":"emoji","category":"类别","title":"标题","content":"内容"}}]}}"""

    try:
        raw = await llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        # extract JSON block
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            items = data.get("items", [])
            if items:
                return _render_news_html(items)
    except Exception as e:
        logger.warning("AI news generation failed: %s", e)
    return _static_news_html()


# ---------------------------------------------------------------------------
# Health module helpers
# ---------------------------------------------------------------------------

def _get_reminder(health: dict) -> str:
    if not is_checked_in_today(health):
        return '<div class="exercise-reminder">⚡ 今日还未完成运动打卡，点击「运动健康」进行打卡！</div>'
    return ""


def _render_exercise_cal(year: int, month: int, checkins: dict) -> str:
    from datetime import date
    cal = _calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)
    today = date.today()
    t_str = today.isoformat()
    month_prefix = f"{year:04d}-{month:02d}-"
    count = sum(1 for k in checkins if k.startswith(month_prefix))
    headers = "".join(f"<th>{d}</th>" for d in ["一","二","三","四","五","六","日"])
    rows = ""
    for week in weeks:
        rows += "<tr>"
        for day in week:
            if day == 0:
                rows += '<td></td>'
            else:
                ds = f"{year:04d}-{month:02d}-{day:02d}"
                cls = "cal-day"
                if ds == t_str:
                    cls += " cal-today"
                if ds in checkins:
                    cls += " cal-checked"
                rows += f'<td><div class="{cls}">{day}</div></td>'
        rows += "</tr>"
    return f'''<div class="cal-html-wrap">
<div class="cal-stats">本月已打卡 <strong>{count}</strong> 天</div>
<table class="cal-table"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>
</div>'''


def _render_sleep_log(records: dict) -> str:
    if not records:
        return '<div class="sleep-log-wrap"><p style="color:#9aa5b4;font-size:0.85em;text-align:center;padding:20px 0">暂无睡眠记录</p></div>'
    # Show last 10 days sorted desc
    sorted_days = sorted(records.keys(), reverse=True)[:10]
    stars_map = {1:"★☆☆☆☆",2:"★★☆☆☆",3:"★★★☆☆",4:"★★★★☆",5:"★★★★★"}
    entries = ""
    for d in sorted_days:
        r = records[d]
        st = r.get("sleep_time","--")
        wt = r.get("wake_time","--")
        q = r.get("quality", 3)
        dur = r.get("duration","")
        dur_txt = f"{dur}h" if dur else ""
        js = (
            f"var t=document.querySelector('#sleep-del-input textarea');"
            f"if(t){{t.value='{d}';"
            f"t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"
            f"t.dispatchEvent(new Event('change',{{bubbles:true}}));}}"
        )
        entries += f'''<div class="sleep-log-entry">
<span class="sleep-log-date">{d}</span>
<span>{st} → {wt} {dur_txt}</span>
<span class="sleep-quality-stars">{stars_map.get(q,"")}</span>
<span class="sleep-del-btn" onclick="{js}" title="删除">×</span>
</div>'''
    return f'<div class="sleep-log-wrap">{entries}</div>'


# ---------------------------------------------------------------------------
# LLM prompt helpers
# ---------------------------------------------------------------------------

async def _gen_exercise_plan(llm, height, weight, extra_req: str = "") -> str:
    bmi = weight / ((height/100)**2) if height and weight else None
    bmi_txt = f"（BMI约{bmi:.1f}）" if bmi else ""
    extra = f"\n用户额外要求：{extra_req.strip()}" if extra_req and extra_req.strip() else ""
    prompt = f"""你是一名专业健身教练。请根据以下信息为用户制定一份个人化的每周锻炼计划：
身高：{height or '未知'}cm，体重：{weight or '未知'}kg {bmi_txt}{extra}
要求：
- 内容包含每天的锻炼项目、组数/时间、注意事项
- 计划应循序渐进，适合普通人日常坚持
- 总字数200-350字，分天列出（周一到周日格式）
- 不要有多余的前缀或后缀说明，直接给出计划"""
    try:
        return await llm.chat([{"role":"user","content":prompt}], temperature=0.7)
    except Exception as e:
        logger.warning("Exercise plan generation failed: %s", e)
        return "生成失败，请稍后重试。"


async def _gen_nutrition_plan(llm, height, weight) -> str:
    bmi = weight / ((height/100)**2) if height and weight else None
    bmi_txt = f"BMI约{bmi:.1f}，" if bmi else ""
    status = ""
    if bmi:
        if bmi < 18.5:
            status = "偏瘦，需要适当增重"
        elif bmi < 24:
            status = "体重正常"
        elif bmi < 28:
            status = "超重，需要控制饮食"
        else:
            status = "肥胖，需要减重"
    prompt = f"""你是一名注册营养师。请根据以下信息为用户制定个性化的饮食建议：
身高：{height or '未知'}cm，体重：{weight or '未知'}kg，{bmi_txt}状态：{status or '未知'}
要求：
- 分早餐、午餐、晚餐、加餐四部分给出建议
- 说明每日推荐热量摄入范围
- 给出3条具体的日常饮食注意事项
- 总字数200-350字，实用具体
- 直接给出建议，无需多余说明"""
    try:
        return await llm.chat([{"role":"user","content":prompt}], temperature=0.7)
    except Exception as e:
        logger.warning("Nutrition plan generation failed: %s", e)
        return "生成失败，请稍后重试。"


async def _gen_sleep_eval(llm, records: dict) -> str:
    if not records:
        return "暂无睡眠记录，请先记录几天的睡眠数据再进行评估。"
    sorted_days = sorted(records.keys(), reverse=True)[:7]
    lines = []
    for d in sorted_days:
        r = records[d]
        lines.append(f"{d}: 入睡{r.get('sleep_time','?')}, 起床{r.get('wake_time','?')}, 时长{r.get('duration','?')}h, 质量{r.get('quality','?')}/5")
    data_str = "\n".join(lines)
    prompt = f"""你是一名睡眠健康专家。请根据以下近期睡眠记录给出专业的评估与建议：

{data_str}

请从以下几个方面评估（总字数150-250字）：
1. 睡眠规律性评价
2. 睡眠时长评价（成人建议7-9小时）
3. 睡眠质量总体评价
4. 具体改善建议（2-3条）
直接给出评估，无需重复数据。"""
    try:
        return await llm.chat([{"role":"user","content":prompt}], temperature=0.6)
    except Exception as e:
        logger.warning("Sleep evaluation failed: %s", e)
        return "评估失败，请稍后重试。"


# ---------------------------------------------------------------------------
# New module helpers
# ---------------------------------------------------------------------------

def _get_med_reminder(health: dict) -> str:
    unchecked = get_unchecked_med_names(health)
    if unchecked:
        names = "、".join(unchecked[:3]) + ("等" if len(unchecked) > 3 else "")
        return f'<div class="med-reminder">💊 今日未服药提醒：{names}，请记得按时服药！</div>'
    return ""


def _render_med_list(health: dict) -> str:
    meds = health.get("medications", [])
    today = today_str()
    taken_ids = set(health.get("med_checkins", {}).get(today, []))
    if not meds:
        return '<div class="med-list-card"><p style="color:#9aa5b4;font-size:0.85em;text-align:center;padding:10px 0">暂无药品，请在下方添加</p></div>'
    # Build chronic_id → disease name map
    chronic_map = {}
    for cd in health.get("chronic_diseases", []):
        chronic_map[cd["id"]] = cd.get("name", "")
    rows = ""
    for m in meds:
        tid = m["id"]
        taken = tid in taken_ids
        times_str = "·".join(m.get("times", [])) or m.get("frequency", "")
        status = '<span class="med-taken">✓ 已服</span>' if taken else ""
        # Show chronic disease tag if linked
        chronic_tag = ""
        cid = m.get("chronic_id", "")
        if cid and cid in chronic_map:
            chronic_tag = f'<span style="font-size:0.68em;padding:1px 6px;border-radius:8px;background:#fff3e0;color:#e65100;font-weight:600;margin-left:4px">{chronic_map[cid]}</span>'
        js = (
            f"var t=document.querySelector('#med-del-input textarea');"
            f"if(t){{t.value='{tid}';"
            f"t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"
            f"t.dispatchEvent(new Event('change',{{bubbles:true}}));}}"
        )
        rows += f'''<div class="med-row">
<span class="med-name">{m["name"]}</span>
<span class="med-dosage">{m.get("dosage","")}</span>
<span class="med-times">{times_str}</span>
{chronic_tag}{status}
<span class="sleep-del-btn" onclick="{js}" title="删除">×</span>
</div>'''
    return f'<div class="med-list-card">{rows}</div>'


def _render_medical_records(health: dict) -> str:
    recs = health.get("medical_records", [])
    if not recs:
        return '<div class="medrec-empty">暂无病历记录，点击左侧添加</div>'
    sorted_recs = sorted(recs, key=lambda r: r.get("date", ""), reverse=True)
    html = ""
    for r in sorted_recs:
        rid = r["id"]
        src = r.get("source", "manual")
        src_cls = "medrec-source-ai" if src == "diagnosis" else "medrec-source-manual"
        src_label = "AI诊断" if src == "diagnosis" else "手动添加"
        detail_parts = []
        if r.get("diagnosis"):
            detail_parts.append(f'<b>诊断：</b>{r["diagnosis"]}')
        if r.get("treatment"):
            detail_parts.append(f'<b>治疗：</b>{r["treatment"]}')
        if r.get("hospital"):
            detail_parts.append(f'<b>医院：</b>{r["hospital"]}')
        if r.get("note"):
            detail_parts.append(f'<b>备注：</b>{r["note"]}')
        detail_html = "<br>".join(detail_parts) if detail_parts else ""
        # Edit button JS: write "edit|{id}" to hidden input
        js_edit = (
            f"var t=document.querySelector('#medrec-action-input textarea');"
            f"if(t){{t.value='edit|{rid}';"
            f"t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"
            f"t.dispatchEvent(new Event('change',{{bubbles:true}}));}}"
        )
        # Delete button JS: write "del|{id}" to hidden input
        js_del = (
            f"var t=document.querySelector('#medrec-action-input textarea');"
            f"if(t){{t.value='del|{rid}';"
            f"t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"
            f"t.dispatchEvent(new Event('change',{{bubbles:true}}));}}"
        )
        html += f'''<div class="medrec-card">
<div class="medrec-actions">
  <span class="medrec-btn-edit" onclick="{js_edit}" title="编辑">✎</span>
  <span class="medrec-btn-del" onclick="{js_del}" title="删除">×</span>
</div>
<div class="medrec-top">
  <span class="medrec-date">{r.get("date","")}</span>
  <span class="medrec-source {src_cls}">{src_label}</span>
</div>
<div class="medrec-symptom">{r.get("symptom","")}</div>
{"<div class='medrec-detail'>" + detail_html + "</div>" if detail_html else ""}
</div>'''
    return html


def _render_chronic_list(health: dict) -> str:
    cds = health.get("chronic_diseases", [])
    if not cds:
        return '<div class="chronic-empty">暂无慢病记录，点击左侧添加</div>'
    # Build a map: med_id → chronic disease name (for linkage display in med panel)
    html = ""
    for cd in cds:
        cid = cd["id"]
        js_edit = (
            f"var t=document.querySelector('#chronic-action-input textarea');"
            f"if(t){{t.value='edit|{cid}';"
            f"t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"
            f"t.dispatchEvent(new Event('change',{{bubbles:true}}));}}"
        )
        js_del = (
            f"var t=document.querySelector('#chronic-action-input textarea');"
            f"if(t){{t.value='del|{cid}';"
            f"t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"
            f"t.dispatchEvent(new Event('change',{{bubbles:true}}));}}"
        )
        # Medications sub-list
        med_html = ""
        meds = cd.get("medications", [])
        if meds:
            items = ""
            for m in meds:
                dosage = f" {m.get('dosage','')}" if m.get("dosage") else ""
                freq = f" ({m.get('frequency','')})" if m.get("frequency") else ""
                items += f'<div class="chronic-sub-item"><span class="dot"></span>{m["name"]}{dosage}{freq}</div>'
            med_html = f'<div class="chronic-section"><b>💊 用药：</b><div class="chronic-sub-list">{items}</div></div>'
        # Indicators sub-list
        ind_html = ""
        indicators = cd.get("indicators", [])
        if indicators:
            items = ""
            for ind in indicators:
                target = f"（目标：{ind.get('target','')}）" if ind.get("target") else ""
                freq = f" · {ind.get('frequency','')}" if ind.get("frequency") else ""
                items += f'<div class="chronic-sub-item"><span class="dot"></span>{ind["name"]}{target}{freq}</div>'
            ind_html = f'<div class="chronic-section"><b>📊 指标监测：</b><div class="chronic-sub-list">{items}</div></div>'
        note_html = f'<div class="chronic-section"><b>备注：</b>{cd["note"]}</div>' if cd.get("note") else ""
        date_html = f'<span class="chronic-date">确诊 {cd.get("diagnosed_date","")}</span>' if cd.get("diagnosed_date") else ""
        linked = f'<span class="chronic-tag">慢病用药已同步</span>' if meds else ""
        html += f'''<div class="chronic-card">
<div class="chronic-actions">
  <span class="chronic-btn-edit" onclick="{js_edit}" title="编辑">✎</span>
  <span class="chronic-btn-del" onclick="{js_del}" title="删除">×</span>
</div>
<div class="chronic-top"><span class="chronic-name">{cd.get("name","")}</span>{date_html}{linked}</div>
{med_html}{ind_html}{note_html}
</div>'''
    return html


def _render_mood_history(records: dict) -> str:
    if not records:
        return '<p style="color:#9aa5b4;font-size:0.82em">暂无心情记录</p>'
    mood_emoji = {1: "😢", 2: "😟", 3: "😐", 4: "😊", 5: "😄"}
    mood_label = {1: "很差", 2: "较差", 3: "一般", 4: "良好", 5: "极好"}
    sorted_days = sorted(records.keys(), reverse=True)[:30]
    # Dot overview
    dots = ""
    for d in sorted_days:
        mood = records[d].get("mood", 3)
        note = records[d].get("note", "")
        title = f"{d} {mood_emoji.get(mood,'')} {note[:10]}" if note else f"{d} {mood_emoji.get(mood,'')}"
        day_num = d[8:]
        dots += f'<div class="mood-dot mood-{mood}" title="{title}">{day_num}</div>'
    dot_html = f'<div style="margin-bottom:10px;font-size:0.78em;color:#8aaac8">近30天心情（深蓝=极好，绿=良好，黄=一般，橙=较差，红=很差）</div><div class="mood-dot-row">{dots}</div>'
    # Detail list with delete buttons
    rows = ""
    for d in sorted_days[:10]:
        mood = records[d].get("mood", 3)
        note = records[d].get("note", "")
        note_html = f'<span class="mood-rec-note">{note}</span>' if note else ""
        js = (
            f"var t=document.querySelector('#mood-del-input textarea');"
            f"if(t){{t.value='{d}';"
            f"t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"
            f"t.dispatchEvent(new Event('change',{{bubbles:true}}));}}"
        )
        rows += (
            f'<div class="mood-rec-row">'
            f'<span class="mood-rec-date">{d}</span>'
            f'<span class="mood-rec-emoji">{mood_emoji.get(mood, "")}</span>'
            f'<span class="mood-rec-label mood-{mood}">{mood_label.get(mood, "")}</span>'
            f'{note_html}'
            f'<span class="mood-rec-del" onclick="{js}">×</span>'
            f'</div>'
        )
    return dot_html + '<div class="mood-rec-list">' + rows + '</div>'


async def _gen_mental_reply(llm, history: list, user_msg: str) -> str:
    """history is a list of {"role":..., "content":...} dicts (Gradio 6 messages format)."""
    system = """你是一名温暖、专业的心理咨询师。请用关怀、非评判性的语言与用户交流。
你的职责是：倾听用户的情绪和感受，给予情感支持，帮助用户探索内心、缓解压力。
注意：你不是医生，不能做诊断，遇到严重心理问题时请建议用户寻求专业医疗帮助。
用中文回复，语言温和自然，每次回复100-200字。"""
    messages = [{"role": "system", "content": system}]
    for msg in history:
        role = msg.get("role") if isinstance(msg, dict) else None
        content = msg.get("content") if isinstance(msg, dict) else None
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_msg})
    try:
        return await llm.chat(messages, temperature=0.75)
    except Exception as e:
        logger.warning("Mental reply failed: %s", e)
        return "抱歉，我暂时无法回复，请稍后再试。"


def _build_health_context(profile: dict, health: dict) -> str:
    """Build a data summary string from profile + health data for the assistant."""
    parts = []
    # Profile
    p = []
    if profile.get("gender"):
        p.append(f"性别: {profile['gender']}")
    if profile.get("age"):
        p.append(f"年龄: {profile['age']}岁")
    if profile.get("height"):
        p.append(f"身高: {profile['height']}cm")
    if profile.get("weight"):
        p.append(f"体重: {profile['weight']}kg")
    if profile.get("allergy"):
        p.append(f"过敏史: {profile['allergy']}")
    if profile.get("past_history"):
        p.append(f"既往病史: {profile['past_history']}")
    if p:
        parts.append("【个人信息】\n" + "；".join(p))
    # Exercise
    plan = health.get("exercise_plan")
    if plan:
        parts.append(f"【运动计划】\n{plan}")
    checkins = health.get("exercise_checkins", {})
    if checkins:
        recent = sorted(checkins.keys())[-7:]
        parts.append(f"【近期运动打卡】{', '.join(recent)}")
    today = today_str()
    if today not in checkins:
        parts.append("⚡ 今日尚未运动打卡")
    # Nutrition
    nplan = health.get("nutrition_plan")
    if nplan:
        parts.append(f"【营养膳食计划】\n{nplan}")
    # Sleep
    sleep_recs = health.get("sleep_records", {})
    if sleep_recs:
        recent_s = sorted(sleep_recs.keys())[-5:]
        lines = []
        for d in recent_s:
            r = sleep_recs[d]
            lines.append(f"  {d}: {r.get('duration','')}h (质量{r.get('quality','')})")
        parts.append("【近期睡眠记录】\n" + "\n".join(lines))
    # Mood
    mood_recs = health.get("mood_records", {})
    if mood_recs:
        recent_m = sorted(mood_recs.keys())[-5:]
        ml = []
        mood_labels = {1: "很差", 2: "较差", 3: "一般", 4: "良好", 5: "极好"}
        for d in recent_m:
            mr = mood_recs[d]
            score = mr.get("mood", 3)
            note = mr.get("note", "")
            ml.append(f"  {d}: {mood_labels.get(score, score)}" + (f" — {note}" if note else ""))
        parts.append("【近期心情记录】\n" + "\n".join(ml))
    # Medications
    meds = health.get("medications", [])
    if meds:
        med_lines = [f"  {m['name']} {m.get('dosage','')} ({m.get('frequency','')})" for m in meds]
        parts.append("【用药列表】\n" + "\n".join(med_lines))
    unchecked = get_unchecked_med_names(health)
    if unchecked:
        parts.append(f"💊 今日未服药：{'、'.join(unchecked)}")
    # Medical records
    medrecs = health.get("medical_records", [])
    if medrecs:
        recent = sorted(medrecs, key=lambda r: r.get("date", ""), reverse=True)[:5]
        lines = []
        for r in recent:
            line = f"  {r.get('date','')} — {r.get('symptom','')}"
            if r.get("diagnosis"):
                line += f"（诊断：{r['diagnosis']}）"
            lines.append(line)
        parts.append("【近期病历】\n" + "\n".join(lines))
    # Chronic diseases
    cds = health.get("chronic_diseases", [])
    if cds:
        cd_lines = []
        for cd in cds:
            line = f"  {cd.get('name','')}"
            if cd.get("diagnosed_date"):
                line += f"（确诊 {cd['diagnosed_date']}）"
            med_names = [m.get("name","") for m in cd.get("medications", [])]
            if med_names:
                line += f" 用药：{'、'.join(med_names)}"
            ind_names = [i.get("name","") for i in cd.get("indicators", [])]
            if ind_names:
                line += f" 监测：{'、'.join(ind_names)}"
            cd_lines.append(line)
        parts.append("【慢性疾病】\n" + "\n".join(cd_lines))
    return "\n\n".join(parts) if parts else "（暂无健康数据）"


async def _gen_health_reply(llm, profile: dict, health: dict,
                            history: list, user_msg: str) -> str:
    ctx = _build_health_context(profile, health)
    today = today_str()
    system = f"""你是一名智能健康助手，负责为用户提供综合健康建议。你可以参考用户的所有健康数据来回答问题。
请根据用户的实际数据给出个性化、具体的建议。语气友善专业，回复控制在200字以内。
如涉及严重健康问题，请提醒用户及时就医。

今天的日期是：{today}

重要：请重点关注近期（近1-2周内）的健康数据，如最近的运动打卡、睡眠记录、心情变化、服药情况和病历。对于时间较久远的记录（超过一个月），除非用户主动询问或存在长期趋势需要提醒，否则不要主动提及。用户最关心的是当下的健康状态和近期的改善建议。

以下是用户当前的健康数据：
{ctx}"""
    messages = [{"role": "system", "content": system}]
    for msg in history:
        role = msg.get("role") if isinstance(msg, dict) else None
        content = msg.get("content") if isinstance(msg, dict) else None
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_msg})
    try:
        return await llm.chat(messages, temperature=0.7)
    except Exception as e:
        logger.warning("Health assistant reply failed: %s", e)
        return "抱歉，我暂时无法回复，请稍后再试。"


# ---------------------------------------------------------------------------
# Portal builder
# ---------------------------------------------------------------------------

def get_portal_css() -> str:
    return PORTAL_CSS


def create_portal(diagnosis_port: int = 7861,
                  patient_profile: dict | None = None,
                  llm=None) -> gr.Blocks:
    """Create the main portal UI.

    Args:
        diagnosis_port: port where the diagnosis system runs.
        patient_profile: shared mutable dict (read/write across UIs).
        llm: LLMClient for generating AI news (optional).
    """
    if patient_profile is None:
        patient_profile = {}

    with gr.Blocks(title="BUAA-MedAgents · 健康管理智能体") as portal:
        portal.queue()

        # ── Header ──
        gr.HTML("""
        <div class="portal-header">
          <span class="portal-header-icon">🏥</span>
          <div>
            <h1>BUAA-MedAgents · 健康管理智能体</h1>
            <p class="portal-header-sub">AI 驱动的个人健康管理平台</p>
          </div>
        </div>""")

        # ── Body ──
        with gr.Row(elem_classes=["portal-body-row"]):

            # ======= SIDEBAR =======
            with gr.Column(scale=1, min_width=170, elem_classes=["portal-sidebar-col"]):

                gr.HTML('<p class="sidebar-section-label">导航</p>')

                home_btn = gr.Button("🏠  首页",
                                     elem_classes=["nav-btn-active"])
                profile_btn = gr.Button("👤  个人信息",
                                        elem_classes=["nav-btn"])

                gr.HTML('<div class="sidebar-sep"></div>')
                gr.HTML('<p class="sidebar-section-label">功能模块</p>')

                diagnosis_btn = gr.Button("🩺  智能诊疗",
                                          elem_classes=["nav-btn"])

                exercise_btn = gr.Button("🏃  运动健康", elem_classes=["nav-btn"])
                nutrition_btn = gr.Button("🥗  营养膳食", elem_classes=["nav-btn"])
                sleep_btn = gr.Button("😴  睡眠管理", elem_classes=["nav-btn"])

                mental_btn = gr.Button("🧠  心理健康", elem_classes=["nav-btn"])
                med_btn = gr.Button("💊  用药管理", elem_classes=["nav-btn"])
                record_btn = gr.Button("📋  健康档案", elem_classes=["nav-btn"])
                chronic_btn = gr.Button("👴  慢病管理", elem_classes=["nav-btn"])

                gr.HTML("""
<div style="opacity:.3;pointer-events:none">
  <div style="display:flex;align-items:center;gap:10px;padding:10px 16px;font-size:.88em;color:rgba(220,230,245,.75)">
    <span>🚑</span><span style="flex:1">急救指南</span>
    <span style="font-size:.6em;padding:1px 6px;border-radius:8px;background:rgba(255,255,255,.08);color:rgba(200,210,230,.6)">即将上线</span>
  </div>
</div>""")

                gr.HTML('<div class="sidebar-sep" style="margin-top:auto"></div>')
                exit_btn = gr.Button("⏻  退出系统",
                                     elem_classes=["nav-btn-exit"])
                exit_status = gr.HTML("")

            # ======= CONTENT =======
            with gr.Column(scale=5, min_width=500, elem_classes=["portal-content-col"]):

                # ── HOME PANEL ──
                with gr.Column(visible=True, elem_classes=["content-panel"]) as home_panel:
                    exercise_reminder = gr.HTML(_get_reminder(load_health()))
                    med_reminder = gr.HTML(_get_med_reminder(load_health()))
                    with gr.Row(elem_classes=["home-row"]):
                        # Left: news
                        with gr.Column(scale=3, min_width=300, elem_classes=["home-left-col"]):
                            with gr.Column(elem_classes=["news-gr-col"]):
                                with gr.Row(elem_classes=["news-title-row"]):
                                    gr.HTML('<p class="news-section-head">今日健康资讯</p>')
                                    refresh_btn = gr.Button(
                                        "🔄 AI 刷新",
                                        elem_classes=["btn-refresh-news"],
                                    )
                                news_html = gr.HTML(_static_news_html())

                        # Right: health assistant chat
                        with gr.Column(scale=4, min_width=300, elem_classes=["home-chat-col"]):
                            gr.HTML('<div class="home-chat-header">🤖 智能健康助手</div>')
                            gr.HTML('<div class="home-chat-sub">基于您的健康数据，为您提供个性化建议。试试问：「我最近睡眠怎么样？」「今天该吃什么药？」</div>')
                            with gr.Column(elem_classes=["home-chat-wrap"]):
                                home_chat_state = gr.State([])
                                home_chatbot = gr.Chatbot(
                                    value=[],
                                    height=400,
                                    elem_classes=["chatbot"],
                                )
                                with gr.Row(elem_classes=["home-chat-input-row"]):
                                    home_chat_input = gr.Textbox(
                                        placeholder="输入健康相关问题…",
                                        show_label=False,
                                        lines=1,
                                        scale=6,
                                        elem_classes=["info-input"],
                                    )
                                    home_send_btn = gr.Button("发送", elem_classes=["btn-home-send"], scale=1)
                                    home_clear_btn = gr.Button("清空", elem_classes=["btn-home-clear"], scale=1)

                    gr.HTML('<div class="portal-footer">BUAA-MedAgents &copy; 2026 · 本系统不构成医疗意见，仅供学习与科研使用</div>')

                # ── PROFILE PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as profile_panel:
                    gr.HTML("""
                    <div class="profile-header">
                      <h2>👤 个人信息管理</h2>
                      <p>信息将自动保存并同步到所有功能模块</p>
                    </div>""")

                    with gr.Column(elem_classes=["profile-form-card"]):
                        with gr.Row():
                            p_gender = gr.Radio(
                                choices=["男", "女"],
                                value=patient_profile.get("gender"),
                                label="性别",
                                elem_classes=["gender-radio", "info-input"],
                            )
                            p_age = gr.Number(
                                label="年龄（岁）",
                                minimum=0, maximum=150,
                                value=patient_profile.get("age"),
                                elem_classes=["info-input"],
                            )
                        with gr.Row():
                            p_height = gr.Number(
                                label="身高（cm）",
                                minimum=0, maximum=300,
                                value=patient_profile.get("height"),
                                elem_classes=["info-input"],
                            )
                            p_weight = gr.Number(
                                label="体重（kg）",
                                minimum=0, maximum=500,
                                value=patient_profile.get("weight"),
                                elem_classes=["info-input"],
                            )
                        p_allergy = gr.Textbox(
                            label="过敏史",
                            placeholder="如：青霉素、磺胺类",
                            value=patient_profile.get("allergy", ""),
                            lines=2, max_lines=3,
                            elem_classes=["info-input"],
                        )
                        p_history = gr.Textbox(
                            label="既往病史",
                            placeholder="如：高血压、糖尿病",
                            value=patient_profile.get("past_history", ""),
                            lines=2, max_lines=3,
                            elem_classes=["info-input"],
                        )
                        with gr.Row():
                            save_btn = gr.Button("保存信息", elem_classes=["btn-save"])
                            save_status = gr.HTML("")

                # ── EXERCISE PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as exercise_panel:
                    gr.HTML("""
                    <div class="module-header">
                      <h2>🏃 运动健康</h2>
                      <p>查看个人锻炼计划，记录每日运动打卡</p>
                    </div>""")
                    with gr.Row():
                        with gr.Column(scale=3):
                            # Plan section
                            plan_req_in = gr.Textbox(
                                label="锻炼要求（可选）",
                                placeholder="如：注重核心力量、每天不超过30分钟、低强度有氧为主…",
                                lines=2,
                                max_lines=3,
                                elem_classes=["info-input"],
                            )
                            with gr.Row():
                                gen_plan_btn = gr.Button("✨ AI生成锻炼计划", elem_classes=["btn-action"])
                            plan_html = gr.Markdown("*暂未生成锻炼计划，点击上方按钮生成*")

                            # Calendar section
                            gr.HTML('<div style="margin-top:16px;margin-bottom:8px;font-size:0.9em;font-weight:600;color:#1a3c6e">📅 打卡日历</div>')
                            with gr.Row(elem_classes=["cal-nav-row"]):
                                prev_month_btn = gr.Button("◀", elem_classes=["btn-cal-nav"])
                                month_label_html = gr.HTML(
                                    f'<p class="cal-month-label">{datetime.now().year}年{datetime.now().month:02d}月</p>'
                                )
                                next_month_btn = gr.Button("▶", elem_classes=["btn-cal-nav"])
                            cal_html_display = gr.HTML(
                                _render_exercise_cal(datetime.now().year, datetime.now().month, {})
                            )

                        with gr.Column(scale=2):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">📊 本月统计</div>')
                            exercise_stats_html = gr.HTML('<div class="cal-html-wrap"><p style="color:#9aa5b4;font-size:0.85em;text-align:center;padding:20px 0">导航到此页面后统计将自动更新</p></div>')
                            checkin_btn = gr.Button("打卡今日", elem_classes=["btn-checkin"])
                    gr.HTML('<div class="module-panel-bottom"></div>')

                # ── NUTRITION PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as nutrition_panel:
                    gr.HTML("""
                    <div class="module-header">
                      <h2>🥗 营养膳食</h2>
                      <p>基于个人体征数据，AI为您定制专属饮食建议</p>
                    </div>""")
                    profile_notice_html = gr.HTML("")
                    with gr.Row():
                        gen_nutrition_btn = gr.Button("✨ AI生成饮食建议", elem_classes=["btn-action"])
                    nutrition_html = gr.Markdown("*暂未生成饮食建议，点击上方按钮生成*")
                    gr.HTML('<div class="module-panel-bottom"></div>')

                # ── SLEEP PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as sleep_panel:
                    gr.HTML("""
                    <div class="module-header">
                      <h2>😴 睡眠管理</h2>
                      <p>记录每日睡眠数据，AI评估睡眠健康状况</p>
                    </div>""")
                    with gr.Row():
                        with gr.Column(scale=3):
                            with gr.Column(elem_classes=["sleep-form-card"]):
                                gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:12px">记录睡眠</div>')
                                from datetime import date, timedelta
                                _yesterday = (date.today() - timedelta(days=1)).isoformat()
                                sleep_date_in = gr.Textbox(
                                    label="日期（默认昨晚）",
                                    value=_yesterday,
                                    placeholder="YYYY-MM-DD",
                                    elem_classes=["info-input"],
                                )
                                with gr.Row():
                                    sleep_time_in = gr.Textbox(
                                        label="入睡时间",
                                        value="23:00",
                                        placeholder="HH:MM",
                                        elem_classes=["info-input"],
                                    )
                                    wake_time_in = gr.Textbox(
                                        label="起床时间",
                                        value="07:00",
                                        placeholder="HH:MM",
                                        elem_classes=["info-input"],
                                    )
                                quality_slider = gr.Slider(
                                    minimum=1, maximum=5, step=1,
                                    value=3,
                                    label="睡眠质量",
                                )
                                sleep_note_in = gr.Textbox(
                                    label="备注（可选）",
                                    placeholder="如：多梦、早醒等",
                                    lines=2,
                                    elem_classes=["info-input"],
                                )
                                with gr.Row():
                                    sleep_save_btn = gr.Button("记录睡眠", elem_classes=["btn-save"])
                                    sleep_save_status = gr.HTML("")
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">近期睡眠记录</div>')
                            sleep_log_html = gr.HTML(_render_sleep_log({}))
                            # CSS-visible (height:0) so JS can find and trigger it
                            sleep_del_input = gr.Textbox(
                                value="",
                                elem_id="sleep-del-input",
                                elem_classes=["sleep-del-hidden"],
                                label="",
                            )

                        with gr.Column(scale=2):
                            with gr.Row():
                                gen_sleep_eval_btn = gr.Button("🔍 AI评估近期睡眠", elem_classes=["btn-action"])
                            sleep_eval_html = gr.Markdown("")
                    gr.HTML('<div class="module-panel-bottom"></div>')

                # ── MENTAL HEALTH PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as mental_panel:
                    gr.HTML("""<div class="module-header"><h2>🧠 心理健康</h2>
      <p>记录每日心情，与AI心理咨询师倾诉</p></div>""")
                    with gr.Row():
                        with gr.Column(scale=3):
                            with gr.Column(elem_classes=["sleep-form-card"]):
                                gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:12px">今日心情记录</div>')
                                from datetime import date as _date
                                mood_date_in = gr.Textbox(label="日期", value=_date.today().isoformat(),
                                    placeholder="YYYY-MM-DD", elem_classes=["info-input"])
                                mood_slider = gr.Slider(minimum=1, maximum=5, step=1, value=3,
                                    label="心情评分（1=很差 5=极好）")
                                mood_note_in = gr.Textbox(label="心情备注（可选）",
                                    placeholder="今天发生了什么……", lines=2, elem_classes=["info-input"])
                                with gr.Row():
                                    mood_save_btn = gr.Button("记录心情", elem_classes=["btn-save"])
                                    mood_save_status = gr.HTML("")
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin:14px 0 8px">近期心情</div>')
                            mood_history_html = gr.HTML(_render_mood_history({}))
                            mood_del_input = gr.Textbox(
                                value="", elem_id="mood-del-input",
                                elem_classes=["sleep-del-hidden"], label="",
                            )
                        with gr.Column(scale=2, elem_classes=["mental-chat-wrap"]):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">💬 AI 心理咨询师</div>')
                            mental_chat_state = gr.State([])
                            mental_chatbot = gr.Chatbot(height=360, label="")
                            with gr.Row(elem_classes=["mental-input-row"]):
                                mental_input = gr.Textbox(placeholder="说说你的感受…", show_label=False,
                                    lines=2, scale=4, elem_classes=["info-input"])
                                mental_send_btn = gr.Button("发送", elem_classes=["btn-action"], scale=1)
                            mental_clear_btn = gr.Button("清空对话", elem_classes=["btn-action-outline"])
                    gr.HTML('<div class="module-panel-bottom"></div>')

                # ── MEDICATION MANAGEMENT PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as med_panel:
                    gr.HTML("""<div class="module-header"><h2>💊 用药管理</h2>
      <p>管理常用药品，记录每日服药情况</p></div>""")
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">我的药品</div>')
                            med_list_html = gr.HTML(_render_med_list(load_health()))
                            with gr.Column(elem_classes=["med-add-form"]):
                                gr.HTML('<div style="font-size:0.88em;font-weight:600;color:#1a3c6e;margin-bottom:10px">添加药品</div>')
                                with gr.Row():
                                    med_name_in = gr.Textbox(label="药品名称", placeholder="如：阿司匹林",
                                        scale=2, elem_classes=["info-input"])
                                    med_dosage_in = gr.Textbox(label="剂量", placeholder="如：100mg",
                                        scale=1, elem_classes=["info-input"])
                                med_times_in = gr.CheckboxGroup(
                                    choices=["早", "中", "晚"], label="服药时间", value=["早"])
                                med_freq_in = gr.Textbox(label="频次", value="每日一次",
                                    placeholder="如：每日一次", elem_classes=["info-input"])
                                with gr.Row():
                                    med_add_btn = gr.Button("+ 添加", elem_classes=["btn-action"])
                                    med_add_status = gr.HTML("")
                            med_del_status = gr.HTML("")
                            med_del_input = gr.Textbox(
                                value="", elem_id="med-del-input",
                                elem_classes=["sleep-del-hidden"], label="",
                            )
                        with gr.Column(scale=2):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">今日服药打卡</div>')
                            med_checkin_group = gr.CheckboxGroup(choices=[], label="", interactive=True)
                            med_checkin_btn = gr.Button("✅ 记录今日服药", elem_classes=["btn-checkin"])
                            med_checkin_status = gr.HTML("")
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin:14px 0 6px">今日服药详情</div>')
                            med_today_html = gr.HTML("")
                    gr.HTML('<div class="module-panel-bottom"></div>')

                # ── MEDICAL RECORDS PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as record_panel:
                    gr.HTML("""<div class="module-header"><h2>📋 健康档案</h2>
      <p>记录病历信息，支持手动添加和AI诊断导入</p></div>""")
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">添加/编辑病历</div>')
                            with gr.Column(elem_classes=["medrec-form-card"]):
                                medrec_edit_id = gr.Textbox(value="", visible=False, elem_id="medrec-edit-id")
                                medrec_form_title = gr.HTML('<span style="font-size:0.85em;color:#5a7fa8">新增病历</span>')
                                medrec_date_in = gr.Textbox(
                                    label="就诊日期", value=today_str(),
                                    placeholder="YYYY-MM-DD", elem_classes=["info-input"])
                                medrec_symptom_in = gr.Textbox(
                                    label="病症/主诉", placeholder="如：反复咳嗽一周",
                                    elem_classes=["info-input"])
                                medrec_diagnosis_in = gr.Textbox(
                                    label="诊断结果", placeholder="如：急性支气管炎",
                                    elem_classes=["info-input"])
                                medrec_treatment_in = gr.Textbox(
                                    label="治疗方案", placeholder="如：头孢克肟 + 止咳糖浆",
                                    lines=2, elem_classes=["info-input"])
                                medrec_hospital_in = gr.Textbox(
                                    label="医院/医生（可选）", placeholder="如：北京某医院",
                                    elem_classes=["info-input"])
                                medrec_note_in = gr.Textbox(
                                    label="备注（可选）", placeholder="其他信息",
                                    lines=2, elem_classes=["info-input"])
                                with gr.Row():
                                    medrec_save_btn = gr.Button("保存病历", elem_classes=["btn-save"])
                                    medrec_cancel_btn = gr.Button("取消编辑", elem_classes=["btn-home-clear"], visible=False)
                                    medrec_save_status = gr.HTML("")
                        with gr.Column(scale=4):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">病历列表</div>')
                            medrec_list_html = gr.HTML(_render_medical_records(load_health()))
                            medrec_action_input = gr.Textbox(
                                value="", elem_id="medrec-action-input",
                                elem_classes=["sleep-del-hidden"], label="",
                            )
                    gr.HTML('<div class="module-panel-bottom"></div>')

                # ── CHRONIC DISEASE PANEL ──
                with gr.Column(visible=False, elem_classes=["content-panel"]) as chronic_panel:
                    gr.HTML("""<div class="module-header"><h2>👴 慢病管理</h2>
      <p>管理慢性疾病信息、关联用药和指标监测</p></div>""")
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">添加/编辑慢病</div>')
                            with gr.Column(elem_classes=["chronic-form-card"]):
                                chronic_edit_id = gr.Textbox(value="", visible=False, elem_id="chronic-edit-id")
                                chronic_form_title = gr.HTML('<span style="font-size:0.85em;color:#e65100">新增慢病</span>')
                                chronic_name_in = gr.Textbox(
                                    label="病症名称", placeholder="如：2型糖尿病、高血压",
                                    elem_classes=["info-input"])
                                chronic_date_in = gr.Textbox(
                                    label="确诊日期（可选）", placeholder="YYYY-MM-DD",
                                    elem_classes=["info-input"])
                                # Medications sub-form
                                gr.HTML('<div style="font-size:0.85em;font-weight:600;color:#4a6580;margin:10px 0 4px">💊 关联用药</div>')
                                chronic_meds_sub_html = gr.HTML('<div style="color:#999;font-size:0.82em">暂无关联用药</div>')
                                with gr.Row():
                                    chronic_med_name = gr.Textbox(label="药名", placeholder="如：二甲双胍", scale=2, elem_classes=["info-input"])
                                    chronic_med_dosage = gr.Textbox(label="剂量", placeholder="如：500mg", scale=1, elem_classes=["info-input"])
                                    chronic_med_freq = gr.Textbox(label="频次", placeholder="如：每日两次", scale=1, elem_classes=["info-input"])
                                chronic_med_add_btn = gr.Button("+ 添加用药", size="sm", elem_classes=["btn-action"])
                                chronic_med_del_input = gr.Textbox(value="", elem_id="chronic-med-del", elem_classes=["sleep-del-hidden"], label="")
                                # Indicators sub-form
                                gr.HTML('<div style="font-size:0.85em;font-weight:600;color:#4a6580;margin:10px 0 4px">📊 指标监测</div>')
                                chronic_inds_sub_html = gr.HTML('<div style="color:#999;font-size:0.82em">暂无指标监测</div>')
                                with gr.Row():
                                    chronic_ind_name = gr.Textbox(label="指标名", placeholder="如：空腹血糖", scale=2, elem_classes=["info-input"])
                                    chronic_ind_target = gr.Textbox(label="目标值", placeholder="如：<7.0mmol/L", scale=1, elem_classes=["info-input"])
                                    chronic_ind_freq = gr.Textbox(label="检测频次", placeholder="如：每日", scale=1, elem_classes=["info-input"])
                                chronic_ind_add_btn = gr.Button("+ 添加指标", size="sm", elem_classes=["btn-action"])
                                chronic_ind_del_input = gr.Textbox(value="", elem_id="chronic-ind-del", elem_classes=["sleep-del-hidden"], label="")
                                chronic_note_in = gr.Textbox(
                                    label="备注（可选）", placeholder="注意事项等",
                                    lines=2, elem_classes=["info-input"])
                                with gr.Row():
                                    chronic_save_btn = gr.Button("保存", elem_classes=["btn-save"])
                                    chronic_cancel_btn = gr.Button("取消编辑", elem_classes=["btn-home-clear"], visible=False)
                                    chronic_save_status = gr.HTML("")
                        with gr.Column(scale=4):
                            gr.HTML('<div style="font-size:0.9em;font-weight:600;color:#1a3c6e;margin-bottom:8px">慢病列表</div>')
                            chronic_list_html = gr.HTML(_render_chronic_list(load_health()))
                            chronic_action_input = gr.Textbox(
                                value="", elem_id="chronic-action-input",
                                elem_classes=["sleep-del-hidden"], label="",
                            )
                    gr.HTML('<div class="module-panel-bottom"></div>')

        # ── States ──
        cal_state = gr.State([datetime.now().year, datetime.now().month])
        chronic_meds_state = gr.State([])
        chronic_inds_state = gr.State([])

        # ── Events ──

        # Navigation helper
        def _nav_updates(active: str, *extra):
            """Returns visibility updates for 9 panels + class updates for 9 nav buttons."""
            names = ["home", "profile", "exercise", "nutrition", "sleep", "mental", "med", "record", "chronic"]
            p = [gr.update(visible=(n == active)) for n in names]
            b = [gr.update(elem_classes=["nav-btn-active" if n == active else "nav-btn"]) for n in names]
            return tuple(p + b + list(extra))

        # Navigation: Home
        def go_home(chat_hist):
            health = load_health()
            ex_reminder = _get_reminder(health)
            med_reminder_val = _get_med_reminder(health)
            return (
                *_nav_updates("home"),
                gr.update(value=ex_reminder),
                gr.update(value=med_reminder_val),
                chat_hist or [],
            )

        home_btn.click(
            fn=go_home,
            inputs=[home_chat_state],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel,
                     mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn,
                     mental_btn, med_btn, record_btn, chronic_btn,
                     exercise_reminder, med_reminder, home_chatbot],
        )

        # Navigation: Profile — always reads fresh data from disk
        def go_profile():
            fresh = load_profile()
            patient_profile.update(fresh)  # sync in-memory
            return (
                *_nav_updates("profile"),
                gr.update(value=fresh.get("gender")),
                gr.update(value=fresh.get("age")),
                gr.update(value=fresh.get("height")),
                gr.update(value=fresh.get("weight")),
                gr.update(value=fresh.get("allergy", "")),
                gr.update(value=fresh.get("past_history", "")),
                gr.update(value=""),
            )

        profile_btn.click(
            fn=go_profile,
            inputs=[],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel,
                     mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn,
                     mental_btn, med_btn, record_btn, chronic_btn,
                     p_gender, p_age, p_height, p_weight, p_allergy, p_history,
                     save_status],
        )

        # Navigation: Diagnosis (same-tab)
        diagnosis_btn.click(
            fn=lambda: None,
            inputs=[], outputs=[],
            js=f"() => {{ window.location.href = 'http://127.0.0.1:{diagnosis_port}'; }}",
        )

        # Navigation: Exercise
        def go_exercise():
            health = load_health()
            yr, mo = datetime.now().year, datetime.now().month
            cal_html = _render_exercise_cal(yr, mo, health.get("exercise_checkins", {}))
            plan = health.get("exercise_plan")
            if plan:
                plan_text = f'> 生成时间：{plan.get("generated_at","")} · 身高 {plan.get("height","")}cm / 体重 {plan.get("weight","")}kg\n\n{plan.get("content","")}'
            else:
                plan_text = '*暂未生成锻炼计划，点击上方按钮生成*'
            today_checked = is_checked_in_today(health)
            checkin_label = "✅ 今日已打卡" if today_checked else "打卡今日"
            checkin_cls = ["btn-checkin-done"] if today_checked else ["btn-checkin"]
            month_label = f"{yr}年{mo:02d}月"
            checkins = health.get("exercise_checkins", {})
            month_prefix = f"{yr:04d}-{mo:02d}-"
            count = sum(1 for k in checkins if k.startswith(month_prefix))
            stats_html = f'<div class="cal-html-wrap"><p style="font-size:0.95em;color:#1a3c6e;font-weight:600;text-align:center;padding:16px 0">本月已打卡<br><span style="font-size:2em;color:#43a047">{count}</span> 天</p></div>'
            return (
                *_nav_updates("exercise"),
                cal_html,
                plan_text,
                gr.update(value=checkin_label, elem_classes=checkin_cls),
                gr.update(value=f'<p class="cal-month-label">{month_label}</p>'),
                stats_html,
            )

        exercise_btn.click(
            fn=go_exercise,
            inputs=[],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel,
                     mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn,
                     mental_btn, med_btn, record_btn, chronic_btn,
                     cal_html_display, plan_html, checkin_btn, month_label_html,
                     exercise_stats_html],
        )

        # Calendar navigation
        def cal_prev(ym):
            yr, mo = ym
            mo -= 1
            if mo < 1:
                mo = 12
                yr -= 1
            health = load_health()
            return [yr, mo], _render_exercise_cal(yr, mo, health.get("exercise_checkins", {})), f'<p class="cal-month-label">{yr}年{mo:02d}月</p>'

        def cal_next(ym):
            yr, mo = ym
            mo += 1
            if mo > 12:
                mo = 1
                yr += 1
            health = load_health()
            return [yr, mo], _render_exercise_cal(yr, mo, health.get("exercise_checkins", {})), f'<p class="cal-month-label">{yr}年{mo:02d}月</p>'

        prev_month_btn.click(
            fn=cal_prev,
            inputs=[cal_state],
            outputs=[cal_state, cal_html_display, month_label_html],
        )

        next_month_btn.click(
            fn=cal_next,
            inputs=[cal_state],
            outputs=[cal_state, cal_html_display, month_label_html],
        )

        # Check-in
        def do_checkin():
            health = load_health()
            health["exercise_checkins"][today_str()] = True
            save_health(health)
            yr, mo = datetime.now().year, datetime.now().month
            cal_html = _render_exercise_cal(yr, mo, health["exercise_checkins"])
            reminder = _get_reminder(health)
            return cal_html, gr.update(value="✅ 今日已打卡", elem_classes=["btn-checkin-done"]), reminder

        checkin_btn.click(
            fn=do_checkin,
            inputs=[],
            outputs=[cal_html_display, checkin_btn, exercise_reminder],
        )

        # Generate exercise plan
        async def gen_exercise_plan(extra_req):
            yield gr.update(value='*⏳ AI 正在生成锻炼计划…*')
            profile = load_profile()
            h, w = profile.get("height"), profile.get("weight")
            if llm is None:
                yield gr.update(value='*未配置 LLM，无法生成*')
                return
            content = await _gen_exercise_plan(llm, h, w, extra_req)
            health = load_health()
            health["exercise_plan"] = {
                "content": content,
                "generated_at": today_str(),
                "height": h,
                "weight": w,
            }
            save_health(health)
            plan_text = f'> 生成时间：{today_str()} · 身高 {h}cm / 体重 {w}kg\n\n{content}'
            yield gr.update(value=plan_text)

        gen_plan_btn.click(
            fn=gen_exercise_plan,
            inputs=[plan_req_in],
            outputs=[plan_html],
        )

        # Navigation: Nutrition
        def go_nutrition():
            health = load_health()
            plan = health.get("nutrition_plan")
            if plan:
                n_text = f'> 生成时间：{plan.get("generated_at","")} · 身高 {plan.get("height","")}cm / 体重 {plan.get("weight","")}kg\n\n{plan.get("content","")}'
            else:
                n_text = '*暂未生成饮食建议，点击下方按钮生成*'
            profile = load_profile()
            h = profile.get("height")
            w = profile.get("weight")
            if h and w:
                notice = f'<div style="font-size:0.82em;color:#5a7fa8;margin-bottom:14px;padding:8px 14px;background:#eef3fb;border-radius:8px">当前档案：身高 {h}cm · 体重 {w}kg</div>'
            else:
                notice = '<div style="font-size:0.82em;color:#e65100;margin-bottom:14px;padding:8px 14px;background:#fff3e0;border-radius:8px">⚠️ 请先在「个人信息」中填写身高和体重，以获得更准确的建议</div>'
            return (*_nav_updates("nutrition"), n_text, notice)

        nutrition_btn.click(
            fn=go_nutrition,
            inputs=[],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel,
                     mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn,
                     mental_btn, med_btn, record_btn, chronic_btn,
                     nutrition_html, profile_notice_html],
        )

        async def gen_nutrition_plan():
            yield gr.update(value='*⏳ AI 正在生成饮食建议…*')
            profile = load_profile()
            h, w = profile.get("height"), profile.get("weight")
            if llm is None:
                yield gr.update(value='*未配置 LLM，无法生成*')
                return
            content = await _gen_nutrition_plan(llm, h, w)
            health = load_health()
            health["nutrition_plan"] = {
                "content": content,
                "generated_at": today_str(),
                "height": h,
                "weight": w,
            }
            save_health(health)
            n_text = f'> 生成时间：{today_str()} · 身高 {h}cm / 体重 {w}kg\n\n{content}'
            yield gr.update(value=n_text)

        gen_nutrition_btn.click(
            fn=gen_nutrition_plan,
            inputs=[],
            outputs=[nutrition_html],
        )

        # Navigation: Sleep
        def go_sleep():
            health = load_health()
            records = health.get("sleep_records", {})
            log_html = _render_sleep_log(records)
            return (*_nav_updates("sleep"), log_html, "")

        sleep_btn.click(
            fn=go_sleep,
            inputs=[],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel,
                     mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn,
                     mental_btn, med_btn, record_btn, chronic_btn,
                     sleep_log_html, sleep_eval_html],
        )

        def save_sleep(record_date, sleep_time, wake_time, quality, note):
            # Validate date
            from datetime import datetime as _dt
            date_str = (record_date or "").strip()
            if date_str:
                try:
                    _dt.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    return gr.update(), '<span style="color:#c0504a;font-size:0.82em">⚠ 日期格式错误，请使用 YYYY-MM-DD</span>'
            else:
                date_str = today_str()
            # Calculate duration
            try:
                sh, sm = map(int, sleep_time.split(":"))
                wh, wm = map(int, wake_time.split(":"))
                total_min = (wh * 60 + wm) - (sh * 60 + sm)
                if total_min < 0:
                    total_min += 24 * 60
                duration = round(total_min / 60, 1)
            except Exception:
                duration = None
            health = load_health()
            health["sleep_records"][date_str] = {
                "sleep_time": sleep_time,
                "wake_time": wake_time,
                "quality": int(quality),
                "note": note or "",
                "duration": duration,
            }
            save_health(health)
            return (
                _render_sleep_log(health["sleep_records"]),
                f'<span class="save-ok">✓ 已记录（{date_str}）</span>',
            )

        sleep_save_btn.click(
            fn=save_sleep,
            inputs=[sleep_date_in, sleep_time_in, wake_time_in, quality_slider, sleep_note_in],
            outputs=[sleep_log_html, sleep_save_status],
        )

        def delete_sleep(date_to_del):
            d = (date_to_del or "").strip()
            if not d:
                return gr.update(), gr.update(value=""), gr.update()
            health = load_health()
            health["sleep_records"].pop(d, None)
            save_health(health)
            return (
                _render_sleep_log(health["sleep_records"]),
                gr.update(value=""),   # reset the hidden input
                '<span class="save-ok">✓ 已删除</span>',
            )

        sleep_del_input.change(
            fn=delete_sleep,
            inputs=[sleep_del_input],
            outputs=[sleep_log_html, sleep_del_input, sleep_save_status],
        )

        async def gen_sleep_eval():
            yield gr.update(value='*⏳ AI 正在评估睡眠数据…*')
            if llm is None:
                yield gr.update(value='*未配置 LLM，无法评估*')
                return
            health = load_health()
            records = health.get("sleep_records", {})
            result = await _gen_sleep_eval(llm, records)
            yield gr.update(value=result)

        gen_sleep_eval_btn.click(
            fn=gen_sleep_eval,
            inputs=[],
            outputs=[sleep_eval_html],
        )

        # Save profile
        def on_save(gender_v, age_v, height_v, weight_v, allergy_v, history_v):
            patient_profile["gender"]       = gender_v
            patient_profile["age"]          = age_v
            patient_profile["height"]       = height_v
            patient_profile["weight"]       = weight_v
            patient_profile["allergy"]      = allergy_v or ""
            patient_profile["past_history"] = history_v or ""
            save_profile(patient_profile)
            return gr.update(value='<span class="save-ok">✓ 已保存</span>')

        save_btn.click(
            fn=on_save,
            inputs=[p_gender, p_age, p_height, p_weight, p_allergy, p_history],
            outputs=[save_status],
        )

        # Exit
        def on_exit():
            import os, threading, time
            threading.Thread(
                target=lambda: (time.sleep(0.6), os._exit(0)),
                daemon=True,
            ).start()
            return gr.update(value="<span style='font-size:0.75em;color:rgba(240,130,130,0.8);padding:4px 16px;display:block'>已退出…</span>")

        exit_btn.click(fn=on_exit, inputs=[], outputs=[exit_status])

        # Navigation: Mental Health
        def go_mental(chat_hist):
            health = load_health()
            history_html = _render_mood_history(health.get("mood_records", {}))
            return (*_nav_updates("mental"), history_html, chat_hist or [])

        mental_btn.click(fn=go_mental, inputs=[mental_chat_state],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel, mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn, mental_btn, med_btn, record_btn, chronic_btn,
                     mood_history_html, mental_chatbot])

        # Navigation: Medication Management
        def go_med():
            health = load_health()
            meds = health.get("medications", [])
            today_taken = set(health.get("med_checkins", {}).get(today_str(), []))
            choices = [f'{m["name"]} ({m.get("dosage","")})' for m in meds]
            checked = [f'{m["name"]} ({m.get("dosage","")})' for m in meds if m["id"] in today_taken]
            return (*_nav_updates("med"),
                    _render_med_list(health),
                    gr.update(choices=choices, value=checked),
                    _render_med_list(health), "")

        med_btn.click(fn=go_med, inputs=[],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel, mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn, mental_btn, med_btn, record_btn, chronic_btn,
                     med_list_html, med_checkin_group, med_today_html, med_checkin_status])

        # Navigation: Medical Records
        def go_record():
            health = load_health()
            return (*_nav_updates("record"),
                    _render_medical_records(health))

        record_btn.click(fn=go_record, inputs=[],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel, mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn, mental_btn, med_btn, record_btn, chronic_btn,
                     medrec_list_html])

        # Save / update medical record
        def save_medrec(edit_id, rec_date, symptom, diagnosis, treatment, hospital, note):
            from datetime import datetime as _dt
            d = (rec_date or "").strip()
            if d:
                try:
                    _dt.strptime(d, "%Y-%m-%d")
                except ValueError:
                    return (gr.update(), gr.update(),
                            '<span style="color:#c0504a;font-size:0.82em">⚠ 日期格式无效</span>',
                            gr.update(), gr.update(), gr.update(), gr.update(),
                            gr.update(), gr.update(), gr.update())
            if not (symptom or "").strip():
                return (gr.update(), gr.update(),
                        '<span style="color:#c0504a;font-size:0.82em">⚠ 请填写病症/主诉</span>',
                        gr.update(), gr.update(), gr.update(), gr.update(),
                        gr.update(), gr.update(), gr.update())
            health = load_health()
            eid = (edit_id or "").strip()
            if eid:
                update_medical_record(health, eid,
                    date=d, symptom=symptom.strip(),
                    diagnosis=(diagnosis or "").strip(),
                    treatment=(treatment or "").strip(),
                    hospital=(hospital or "").strip(),
                    note=(note or "").strip())
                msg = "✓ 已更新"
            else:
                add_medical_record(health,
                    record_date=d, symptom=symptom.strip(),
                    diagnosis=(diagnosis or "").strip(),
                    treatment=(treatment or "").strip(),
                    hospital=(hospital or "").strip(),
                    note=(note or "").strip(),
                    source="manual")
                msg = "✓ 已添加"
            save_health(health)
            return (
                _render_medical_records(health),
                gr.update(value=""),           # clear edit_id
                f'<span class="save-ok">{msg}</span>',
                gr.update(value=today_str()),  # reset date
                gr.update(value=""),           # symptom
                gr.update(value=""),           # diagnosis
                gr.update(value=""),           # treatment
                gr.update(value=""),           # hospital
                gr.update(value=""),           # note
                gr.update(visible=False),      # cancel btn
            )

        medrec_save_btn.click(fn=save_medrec,
            inputs=[medrec_edit_id, medrec_date_in, medrec_symptom_in,
                    medrec_diagnosis_in, medrec_treatment_in,
                    medrec_hospital_in, medrec_note_in],
            outputs=[medrec_list_html, medrec_edit_id, medrec_save_status,
                     medrec_date_in, medrec_symptom_in, medrec_diagnosis_in,
                     medrec_treatment_in, medrec_hospital_in, medrec_note_in,
                     medrec_cancel_btn])

        # Cancel editing — reset form
        def cancel_edit_medrec():
            return (
                gr.update(value=""),           # edit_id
                '<span style="font-size:0.85em;color:#5a7fa8">新增病历</span>',
                gr.update(value=today_str()),
                gr.update(value=""), gr.update(value=""),
                gr.update(value=""), gr.update(value=""),
                gr.update(value=""), gr.update(value=""),
                gr.update(visible=False),
            )

        medrec_cancel_btn.click(fn=cancel_edit_medrec, inputs=[],
            outputs=[medrec_edit_id, medrec_form_title,
                     medrec_date_in, medrec_symptom_in, medrec_diagnosis_in,
                     medrec_treatment_in, medrec_hospital_in, medrec_note_in,
                     medrec_save_status, medrec_cancel_btn])

        # Edit / delete medical record (triggered by JS hidden input)
        def medrec_action(action_str):
            val = (action_str or "").strip()
            if not val or "|" not in val:
                return (gr.update(),) * 11
            action, rid = val.split("|", 1)
            health = load_health()
            if action == "del":
                remove_medical_record(health, rid)
                save_health(health)
                return (
                    _render_medical_records(health),
                    gr.update(value=""),  # action_input
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(),
                )
            elif action == "edit":
                rec = next((r for r in health.get("medical_records", []) if r["id"] == rid), None)
                if not rec:
                    return (gr.update(),) * 11
                return (
                    gr.update(),                                        # list (no change)
                    gr.update(value=""),                                 # action_input
                    gr.update(value=rid),                               # edit_id
                    f'<span style="font-size:0.85em;color:#e65100">编辑病历 — {rec.get("symptom","")[:15]}</span>',
                    gr.update(value=rec.get("date", "")),               # date
                    gr.update(value=rec.get("symptom", "")),            # symptom
                    gr.update(value=rec.get("diagnosis", "")),          # diagnosis
                    gr.update(value=rec.get("treatment", "")),          # treatment
                    gr.update(value=rec.get("hospital", "")),           # hospital
                    gr.update(value=rec.get("note", "")),               # note
                    gr.update(visible=True),                            # cancel btn
                )
            return (gr.update(),) * 11

        medrec_action_input.change(fn=medrec_action,
            inputs=[medrec_action_input],
            outputs=[medrec_list_html, medrec_action_input,
                     medrec_edit_id, medrec_form_title,
                     medrec_date_in, medrec_symptom_in, medrec_diagnosis_in,
                     medrec_treatment_in, medrec_hospital_in, medrec_note_in,
                     medrec_cancel_btn])

        # Navigation: Chronic Disease Management
        def go_chronic():
            health = load_health()
            return (*_nav_updates("chronic"),
                    _render_chronic_list(health))

        chronic_btn.click(fn=go_chronic, inputs=[],
            outputs=[home_panel, profile_panel, exercise_panel, nutrition_panel, sleep_panel, mental_panel, med_panel, record_panel, chronic_panel,
                     home_btn, profile_btn, exercise_btn, nutrition_btn, sleep_btn, mental_btn, med_btn, record_btn, chronic_btn,
                     chronic_list_html])

        # Render sub-lists for chronic disease form
        def _render_chronic_meds_sub(meds):
            if not meds:
                return '<div style="color:#999;font-size:0.82em">暂无关联用药</div>'
            html = ''
            for i, m in enumerate(meds):
                label = m.get("name", "")
                if m.get("dosage"):
                    label += f' · {m["dosage"]}'
                if m.get("frequency"):
                    label += f' · {m["frequency"]}'
                html += (f'<div style="display:flex;align-items:center;justify-content:space-between;'
                         f'padding:4px 8px;margin:2px 0;background:#f8f9fa;border-radius:4px;font-size:0.85em">'
                         f'<span>{label}</span>'
                         f'<span style="cursor:pointer;color:#c0504a;font-weight:700" '
                         f"""onclick="(function(){{let t=document.querySelector('#chronic-med-del textarea');"""
                         f"""t.value='';t.dispatchEvent(new Event('input',{{bubbles:true}}));"""
                         f"""setTimeout(()=>{{t.value='{i}';t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"""
                         f"""t.dispatchEvent(new Event('change',{{bubbles:true}}));}},50);}})()">×</span></div>""")
            return html

        def _render_chronic_inds_sub(inds):
            if not inds:
                return '<div style="color:#999;font-size:0.82em">暂无指标监测</div>'
            html = ''
            for i, ind in enumerate(inds):
                label = ind.get("name", "")
                if ind.get("target"):
                    label += f' · {ind["target"]}'
                if ind.get("frequency"):
                    label += f' · {ind["frequency"]}'
                html += (f'<div style="display:flex;align-items:center;justify-content:space-between;'
                         f'padding:4px 8px;margin:2px 0;background:#f8f9fa;border-radius:4px;font-size:0.85em">'
                         f'<span>{label}</span>'
                         f'<span style="cursor:pointer;color:#c0504a;font-weight:700" '
                         f"""onclick="(function(){{let t=document.querySelector('#chronic-ind-del textarea');"""
                         f"""t.value='';t.dispatchEvent(new Event('input',{{bubbles:true}}));"""
                         f"""setTimeout(()=>{{t.value='{i}';t.dispatchEvent(new InputEvent('input',{{bubbles:true}}));"""
                         f"""t.dispatchEvent(new Event('change',{{bubbles:true}}));}},50);}})()">×</span></div>""")
            return html

        # Add / delete handlers for chronic sub-lists
        def add_chronic_med(meds_list, name, dosage, freq):
            if not (name or "").strip():
                return meds_list, _render_chronic_meds_sub(meds_list), gr.update(), gr.update(), gr.update()
            meds_list = list(meds_list)
            meds_list.append({"name": name.strip(), "dosage": (dosage or "").strip(), "frequency": (freq or "").strip()})
            return meds_list, _render_chronic_meds_sub(meds_list), gr.update(value=""), gr.update(value=""), gr.update(value="")

        def del_chronic_med(meds_list, idx_str):
            idx_str = (idx_str or "").strip()
            if not idx_str:
                return meds_list, gr.update(), gr.update(value="")
            try:
                idx = int(idx_str)
                meds_list = list(meds_list)
                if 0 <= idx < len(meds_list):
                    meds_list.pop(idx)
            except ValueError:
                pass
            return meds_list, _render_chronic_meds_sub(meds_list), gr.update(value="")

        def add_chronic_ind(inds_list, name, target, freq):
            if not (name or "").strip():
                return inds_list, _render_chronic_inds_sub(inds_list), gr.update(), gr.update(), gr.update()
            inds_list = list(inds_list)
            inds_list.append({"name": name.strip(), "target": (target or "").strip(), "frequency": (freq or "").strip()})
            return inds_list, _render_chronic_inds_sub(inds_list), gr.update(value=""), gr.update(value=""), gr.update(value="")

        def del_chronic_ind(inds_list, idx_str):
            idx_str = (idx_str or "").strip()
            if not idx_str:
                return inds_list, gr.update(), gr.update(value="")
            try:
                idx = int(idx_str)
                inds_list = list(inds_list)
                if 0 <= idx < len(inds_list):
                    inds_list.pop(idx)
            except ValueError:
                pass
            return inds_list, _render_chronic_inds_sub(inds_list), gr.update(value="")

        # Add / delete sub-list event bindings
        chronic_med_add_btn.click(fn=add_chronic_med,
            inputs=[chronic_meds_state, chronic_med_name, chronic_med_dosage, chronic_med_freq],
            outputs=[chronic_meds_state, chronic_meds_sub_html, chronic_med_name, chronic_med_dosage, chronic_med_freq])

        chronic_med_del_input.change(fn=del_chronic_med,
            inputs=[chronic_meds_state, chronic_med_del_input],
            outputs=[chronic_meds_state, chronic_meds_sub_html, chronic_med_del_input])

        chronic_ind_add_btn.click(fn=add_chronic_ind,
            inputs=[chronic_inds_state, chronic_ind_name, chronic_ind_target, chronic_ind_freq],
            outputs=[chronic_inds_state, chronic_inds_sub_html, chronic_ind_name, chronic_ind_target, chronic_ind_freq])

        chronic_ind_del_input.change(fn=del_chronic_ind,
            inputs=[chronic_inds_state, chronic_ind_del_input],
            outputs=[chronic_inds_state, chronic_inds_sub_html, chronic_ind_del_input])

        # Save / update chronic disease
        def save_chronic(edit_id, name, diagnosed_date, meds_list, inds_list, note):
            if not (name or "").strip():
                return (gr.update(), gr.update(),
                        '<span style="color:#c0504a;font-size:0.82em">⚠ 请填写病症名称</span>',
                        gr.update(), gr.update(), gr.update(),
                        gr.update(), gr.update(), gr.update(),
                        gr.update(), gr.update(), gr.update())
            meds = list(meds_list) if meds_list else []
            indicators = list(inds_list) if inds_list else []
            health = load_health()
            eid = (edit_id or "").strip()
            if eid:
                update_chronic_disease(health, eid,
                    name=name.strip(),
                    diagnosed_date=(diagnosed_date or "").strip(),
                    medications=meds,
                    indicators=indicators,
                    note=(note or "").strip())
                msg = "✓ 已更新"
            else:
                add_chronic_disease(health,
                    name=name.strip(),
                    diagnosed_date=(diagnosed_date or "").strip(),
                    medications=meds,
                    indicators=indicators,
                    note=(note or "").strip())
                msg = "✓ 已添加"
            # Sync meds to global medication list
            sync_chronic_meds_to_medications(health)
            save_health(health)
            empty_meds_html = '<div style="color:#999;font-size:0.82em">暂无关联用药</div>'
            empty_inds_html = '<div style="color:#999;font-size:0.82em">暂无指标监测</div>'
            return (
                _render_chronic_list(health),
                gr.update(value=""),           # edit_id
                f'<span class="save-ok">{msg}</span>',
                gr.update(value=""),           # name
                gr.update(value=""),           # date
                [],                            # meds_state
                empty_meds_html,               # meds_sub_html
                [],                            # inds_state
                empty_inds_html,               # inds_sub_html
                gr.update(value=""),           # note
                gr.update(visible=False),      # cancel btn
                '<span style="font-size:0.85em;color:#e65100">新增慢病</span>',
            )

        chronic_save_btn.click(fn=save_chronic,
            inputs=[chronic_edit_id, chronic_name_in, chronic_date_in,
                    chronic_meds_state, chronic_inds_state, chronic_note_in],
            outputs=[chronic_list_html, chronic_edit_id, chronic_save_status,
                     chronic_name_in, chronic_date_in, chronic_meds_state,
                     chronic_meds_sub_html, chronic_inds_state, chronic_inds_sub_html,
                     chronic_note_in, chronic_cancel_btn, chronic_form_title])

        # Cancel editing chronic disease
        def cancel_edit_chronic():
            empty_meds_html = '<div style="color:#999;font-size:0.82em">暂无关联用药</div>'
            empty_inds_html = '<div style="color:#999;font-size:0.82em">暂无指标监测</div>'
            return (
                gr.update(value=""),
                '<span style="font-size:0.85em;color:#e65100">新增慢病</span>',
                gr.update(value=""), gr.update(value=""),
                [],                  # meds_state
                empty_meds_html,     # meds_sub_html
                [],                  # inds_state
                empty_inds_html,     # inds_sub_html
                gr.update(value=""), gr.update(value=""),
                gr.update(visible=False),
            )

        chronic_cancel_btn.click(fn=cancel_edit_chronic, inputs=[],
            outputs=[chronic_edit_id, chronic_form_title,
                     chronic_name_in, chronic_date_in, chronic_meds_state,
                     chronic_meds_sub_html, chronic_inds_state, chronic_inds_sub_html,
                     chronic_note_in, chronic_save_status, chronic_cancel_btn])

        # Edit / delete chronic disease
        def chronic_action(action_str):
            val = (action_str or "").strip()
            if not val or "|" not in val:
                return (gr.update(),) * 12
            action, cid = val.split("|", 1)
            health = load_health()
            if action == "del":
                remove_chronic_disease(health, cid)
                save_health(health)
                return (
                    _render_chronic_list(health),
                    gr.update(value=""),  # action_input
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(),
                    gr.update(),
                )
            elif action == "edit":
                cd = next((c for c in health.get("chronic_diseases", []) if c["id"] == cid), None)
                if not cd:
                    return (gr.update(),) * 12
                meds = cd.get("medications", [])
                inds = cd.get("indicators", [])
                return (
                    gr.update(),                                             # list
                    gr.update(value=""),                                      # action_input
                    gr.update(value=cid),                                    # edit_id
                    f'<span style="font-size:0.85em;color:#e65100">编辑 — {cd.get("name","")[:15]}</span>',
                    gr.update(value=cd.get("name", "")),                     # name
                    gr.update(value=cd.get("diagnosed_date", "")),           # date
                    meds,                                                    # meds_state
                    _render_chronic_meds_sub(meds),                          # meds_sub_html
                    inds,                                                    # inds_state
                    _render_chronic_inds_sub(inds),                          # inds_sub_html
                    gr.update(value=cd.get("note", "")),                     # note
                    gr.update(visible=True),                                 # cancel btn
                )
            return (gr.update(),) * 12

        chronic_action_input.change(fn=chronic_action,
            inputs=[chronic_action_input],
            outputs=[chronic_list_html, chronic_action_input,
                     chronic_edit_id, chronic_form_title,
                     chronic_name_in, chronic_date_in, chronic_meds_state,
                     chronic_meds_sub_html, chronic_inds_state, chronic_inds_sub_html,
                     chronic_note_in, chronic_cancel_btn])

        # Mood save
        def save_mood(record_date, mood, note):
            from datetime import datetime as _dt
            d = (record_date or "").strip()
            if d:
                try:
                    _dt.strptime(d, "%Y-%m-%d")
                except ValueError:
                    return gr.update(), '<span style="color:#c0504a;font-size:0.82em">⚠ 日期格式错误</span>'
            else:
                d = today_str()
            health = load_health()
            health.setdefault("mood_records", {})[d] = {"mood": int(mood), "note": note or ""}
            save_health(health)
            return _render_mood_history(health["mood_records"]), f'<span class="save-ok">✓ 已记录（{d}）</span>'

        mood_save_btn.click(fn=save_mood,
            inputs=[mood_date_in, mood_slider, mood_note_in],
            outputs=[mood_history_html, mood_save_status])

        # Delete mood record
        def delete_mood(date_key):
            d = (date_key or "").strip()
            if not d:
                return gr.update(), gr.update(value=""), gr.update()
            health = load_health()
            records = health.get("mood_records", {})
            if d in records:
                del records[d]
                save_health(health)
            return (
                _render_mood_history(records),
                gr.update(value=""),
                '<span class="save-ok">✓ 已删除</span>',
            )

        mood_del_input.change(
            fn=delete_mood,
            inputs=[mood_del_input],
            outputs=[mood_history_html, mood_del_input, mood_save_status],
        )

        # Mental chat send
        async def send_mental(user_msg, history):
            if not user_msg.strip():
                yield history, history, ""
                return
            history = list(history or [])
            history.append({"role": "user", "content": user_msg})
            # Show user message + thinking placeholder immediately to keep SSE alive
            history.append({"role": "assistant", "content": "🤔 正在思考中，请稍候…"})
            yield history, history, ""
            if llm is None:
                history[-1] = {"role": "assistant", "content": "（未配置 LLM，无法对话）"}
                yield history, history, ""
                return
            reply = await _gen_mental_reply(llm, history[:-2], user_msg)
            history[-1] = {"role": "assistant", "content": reply}
            yield history, history, ""

        mental_send_btn.click(fn=send_mental,
            inputs=[mental_input, mental_chat_state],
            outputs=[mental_chatbot, mental_chat_state, mental_input])
        mental_input.submit(fn=send_mental,
            inputs=[mental_input, mental_chat_state],
            outputs=[mental_chatbot, mental_chat_state, mental_input])
        mental_clear_btn.click(fn=lambda: ([], []),
            inputs=[], outputs=[mental_chatbot, mental_chat_state])

        # Add medication
        def add_med(name, dosage, times, freq):
            if not name.strip():
                return gr.update(), gr.update(), gr.update(), '<span style="color:#c0504a;font-size:0.82em">⚠ 请输入药品名称</span>'
            health = load_health()
            add_medication(health, name.strip(), dosage.strip(), freq.strip(), times)
            save_health(health)
            meds = health["medications"]
            choices = [f'{m["name"]} ({m.get("dosage","")})' for m in meds]
            return (_render_med_list(health),
                    gr.update(choices=choices, value=[]),
                    gr.update(value=""),
                    '<span class="save-ok">✓ 已添加</span>')

        med_add_btn.click(fn=add_med,
            inputs=[med_name_in, med_dosage_in, med_times_in, med_freq_in],
            outputs=[med_list_html, med_checkin_group, med_name_in, med_add_status])

        # Delete medication (triggered by × button JS writing med ID to hidden textbox)
        def del_med(med_id):
            mid = (med_id or "").strip()
            if not mid:
                return gr.update(), gr.update(), gr.update(value="")
            health = load_health()
            remove_medication(health, mid)
            save_health(health)
            meds = health["medications"]
            choices = [f'{m["name"]} ({m.get("dosage","")})' for m in meds]
            return (_render_med_list(health),
                    gr.update(choices=choices, value=[]),
                    gr.update(value=""))

        med_del_input.change(fn=del_med,
            inputs=[med_del_input],
            outputs=[med_list_html, med_checkin_group, med_del_input])

        # Medication check-in
        def do_med_checkin(checked_display):
            health = load_health()
            meds = health.get("medications", [])
            name_to_id = {f'{m["name"]} ({m.get("dosage","")})': m["id"] for m in meds}
            taken_ids = [name_to_id[c] for c in checked_display if c in name_to_id]
            health.setdefault("med_checkins", {})[today_str()] = taken_ids
            save_health(health)
            med_reminder_html = _get_med_reminder(health)
            today_taken = set(taken_ids)
            rows = ""
            for m in meds:
                taken = m["id"] in today_taken
                status_icon = "✅" if taken else "⬜"
                rows += f'<div class="med-row"><span class="med-name">{m["name"]}</span><span class="med-dosage">{m.get("dosage","")}</span><span>{status_icon} {"已服用" if taken else "未服用"}</span></div>'
            today_html = f'<div class="med-list-card">{rows}</div>' if rows else '<div class="med-list-card"><p style="color:#9aa5b4;font-size:0.85em;text-align:center;padding:8px 0">暂无药品</p></div>'
            return (_render_med_list(health),
                    '<span class="save-ok">✓ 已记录</span>',
                    med_reminder_html,
                    today_html)

        med_checkin_btn.click(fn=do_med_checkin,
            inputs=[med_checkin_group],
            outputs=[med_list_html, med_checkin_status, med_reminder, med_today_html])

        # ── Home health assistant chat ──
        async def send_home_chat(user_msg, history):
            history = list(history or [])
            msg = (user_msg or "").strip()
            if not msg:
                yield history, history, ""
                return
            history.append({"role": "user", "content": msg})
            history.append({"role": "assistant", "content": "🤔 正在思考中，请稍候…"})
            yield history, history, ""
            if llm is None:
                history[-1] = {"role": "assistant", "content": "（未配置 LLM，无法对话）"}
                yield history, history, ""
                return
            health = load_health()
            reply = await _gen_health_reply(llm, patient_profile, health,
                                            history[:-2], msg)
            history[-1] = {"role": "assistant", "content": reply}
            yield history, history, ""

        home_send_btn.click(fn=send_home_chat,
            inputs=[home_chat_input, home_chat_state],
            outputs=[home_chatbot, home_chat_state, home_chat_input])
        home_chat_input.submit(fn=send_home_chat,
            inputs=[home_chat_input, home_chat_state],
            outputs=[home_chatbot, home_chat_state, home_chat_input])
        home_clear_btn.click(fn=lambda: ([], []),
            inputs=[], outputs=[home_chatbot, home_chat_state])

        # Refresh AI news on button click
        async def on_refresh_news():
            yield gr.update(value='<div class="news-loading"><div class="news-spinner"></div> AI 正在生成今日健康资讯…</div>')
            if llm is not None:
                result = await _fetch_ai_news(llm)
            else:
                result = _static_news_html()
            yield gr.update(value=result)

        refresh_btn.click(
            fn=on_refresh_news,
            inputs=[],
            outputs=[news_html],
        )

    return portal
