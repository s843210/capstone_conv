import AsyncStorage from '@react-native-async-storage/async-storage';
import {STORAGE_KEYS} from './appConstants';
import {Suggestion} from '../types';

// 건의사항 목록을 로컬 저장소에서 불러옵니다.
export async function loadSuggestions(): Promise<Suggestion[]> {
  const storedSuggestions = await AsyncStorage.getItem(STORAGE_KEYS.suggestions);
  if (!storedSuggestions) {
    return [];
  }

  try {
    const parsed = JSON.parse(storedSuggestions) as Suggestion[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

// 건의사항 목록을 로컬 저장소에 저장합니다.
export async function saveSuggestions(suggestions: Suggestion[]): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEYS.suggestions, JSON.stringify(suggestions));
}
