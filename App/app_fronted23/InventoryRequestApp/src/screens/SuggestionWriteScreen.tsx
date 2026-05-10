import React, {useState} from 'react';
import {SafeAreaView, Text, TextInput, Pressable, Alert} from 'react-native';
import {Suggestion, SuggestionWriteScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

const MAX_TITLE_LENGTH = 50;
const MIN_CONTENT_LENGTH = 10;

type Props = SuggestionWriteScreenProps & {
  currentUser: string;
  addSuggestion: (suggestion: Suggestion) => Promise<boolean>;
};

export default function SuggestionWriteScreen({navigation, currentUser, addSuggestion}: Props) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitSuggestion = async () => {
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
      // 작성한 건의사항을 앱 내부 목록에 저장
      const suggestion: Suggestion = {
        id: `s-${Date.now()}`,
        title: trimmedTitle,
        content: trimmedContent,
        writer: currentUser,
        createdAt: new Date().toLocaleString('ko-KR'),
      };

      const saved = await addSuggestion(suggestion);
      if (!saved) {
        Alert.alert('저장 오류', '건의사항 저장 중 오류가 발생했습니다.');
        return;
      }

      Alert.alert('등록 완료', '건의사항이 등록되었습니다.');
      navigation.reset({index: 0, routes: [{name: 'ProductList'}]});
    } catch {
      Alert.alert('저장 오류', '건의사항 저장 중 오류가 발생했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>건의사항 작성</Text>
      <Text style={styles.subtitle}>원하는 상품, 이용 불편, 개선 의견을 자유롭게 적어주세요.</Text>

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
        onPress={submitSuggestion}
        disabled={isSubmitting}>
        <Text style={styles.primaryBtnText}>{isSubmitting ? '등록 중...' : '등록'}</Text>
      </Pressable>
    </SafeAreaView>
  );
}
