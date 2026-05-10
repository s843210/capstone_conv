import React, {useState} from 'react';
import {SafeAreaView, Text, TextInput, Pressable, Alert} from 'react-native';
import {Suggestion, SuggestionEditScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

const MAX_TITLE_LENGTH = 50;
const MIN_CONTENT_LENGTH = 10;

type Props = SuggestionEditScreenProps & {
  currentUser: string;
  updateSuggestion: (suggestion: Suggestion, currentUser: string) => Promise<boolean>;
};

export default function SuggestionEditScreen({navigation, route, currentUser, updateSuggestion}: Props) {
  const {suggestion} = route.params;
  const [title, setTitle] = useState(suggestion.title);
  const [content, setContent] = useState(suggestion.content);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitEdit = async () => {
    const trimmedTitle = title.trim();
    const trimmedContent = content.trim();

    if (!trimmedTitle) {
      Alert.alert('입력 오류', '제목을 입력해 주세요.');
      return;
    }
    if (!trimmedContent) {
      Alert.alert('입력 오류', '내용을 입력해 주세요.');
      return;
    }
    if (trimmedTitle.length > MAX_TITLE_LENGTH) {
      Alert.alert('입력 오류', `제목은 ${MAX_TITLE_LENGTH}자 이하로 입력해 주세요.`);
      return;
    }
    if (trimmedContent.length < MIN_CONTENT_LENGTH) {
      Alert.alert('입력 오류', `내용은 최소 ${MIN_CONTENT_LENGTH}자 이상 입력해 주세요.`);
      return;
    }

    setIsSubmitting(true);
    try {
      // 기존 건의사항을 수정해 로컬 목록과 저장소를 갱신
      const nextSuggestion: Suggestion = {
        ...suggestion,
        title: trimmedTitle,
        content: trimmedContent,
        updatedAt: new Date().toLocaleString('ko-KR'),
      };

      const saved = await updateSuggestion(nextSuggestion, currentUser);
      if (!saved) {
        Alert.alert('수정 오류', '건의사항 수정 중 오류가 발생했습니다.');
        return;
      }

      navigation.replace('SuggestionDetail', {suggestion: nextSuggestion});
    } catch {
      Alert.alert('수정 오류', '건의사항 수정 중 오류가 발생했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>건의사항 수정</Text>
      <Text style={styles.subtitle}>작성한 건의사항의 제목과 내용을 수정할 수 있습니다.</Text>

      <TextInput
        placeholder="제목을 입력하세요"
        value={title}
        onChangeText={setTitle}
        style={styles.input}
        editable={!isSubmitting}
      />
      <TextInput
        placeholder="내용을 입력하세요"
        value={content}
        onChangeText={setContent}
        style={[styles.input, {height: 140, textAlignVertical: 'top'}]}
        multiline
        editable={!isSubmitting}
      />

      <Pressable
        style={[styles.primaryBtn, isSubmitting && styles.primaryBtnDisabled]}
        onPress={submitEdit}
        disabled={isSubmitting}>
        <Text style={styles.primaryBtnText}>{isSubmitting ? '저장 중...' : '수정 저장'}</Text>
      </Pressable>
    </SafeAreaView>
  );
}
