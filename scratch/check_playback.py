import asyncio
import sys
import time

async def main():
    try:
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
        
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        session = manager.get_current_session()
        
        if not session:
            print("No active media session found. Make sure Spotify/YouTube is playing.")
            return

        print(f"Active Session Source: {session.source_app_user_model_id}")
        
        props = await session.try_get_media_properties_async()
        if props:
            print(f"Current Track: {props.title} - {props.artist}")
            
        info = session.get_playback_info()
        if info:
            print(f"Playback Status: {info.playback_status} (int: {int(info.playback_status)})")
            print(f"Controls Status: {info.controls_status} (int: {int(info.controls_status)})")
            
        timeline = session.get_timeline_properties()
        if timeline:
            print(f"Timeline Position Ticks: {timeline.position.duration}")
            print(f"Timeline Position Secs: {timeline.position.duration / 10_000_000.0}")
            print(f"Timeline Last Updated: {timeline.last_updated_time}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
